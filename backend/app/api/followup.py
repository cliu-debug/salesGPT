from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_permission, filter_by_organization, check_data_access
from app.models.models import FollowUp, Customer, Opportunity, User
from app.schemas.schemas import FollowUpCreate

router = APIRouter()


@router.post("/", response_model=dict)
async def create_follow_up(
    follow_up_data: FollowUpCreate,
    current_user: User = require_permission("followup:write"),
    db: AsyncSession = Depends(get_db)
):
    """创建跟进记录（需要followup:write权限）"""
    follow_up = FollowUp(
        customer_id=follow_up_data.customer_id,
        customer_name=follow_up_data.customer_name,
        content=follow_up_data.content,
        next_action=follow_up_data.next_action,
        next_date=follow_up_data.next_date,
        # 数据隔离字段
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )
    db.add(follow_up)
    await db.commit()
    await db.refresh(follow_up)
    
    return {
        "id": follow_up.id,
        "customer_id": follow_up.customer_id,
        "created_at": follow_up.created_at,
        "message": "跟进记录创建成功"
    }


@router.get("/", response_model=dict)
async def list_follow_ups(
    page: int = 1,
    size: int = 20,
    customer_id: Optional[int] = None,
    current_user: User = require_permission("followup:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取跟进记录列表（需要followup:read权限，自动数据隔离）"""
    query = select(FollowUp)
    
    # 数据隔离过滤
    query = filter_by_organization(query, FollowUp, current_user)
    
    if customer_id:
        query = query.where(FollowUp.customer_id == customer_id)
    
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    query = query.offset((page - 1) * size).limit(size).order_by(FollowUp.created_at.desc())
    result = await db.execute(query)
    follow_ups = result.scalars().all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": f.id,
                "customer_id": f.customer_id,
                "customer_name": f.customer_name,
                "content": f.content,
                "next_action": f.next_action,
                "next_date": f.next_date,
                "ai_script": f.ai_script,
                "created_at": f.created_at
            }
            for f in follow_ups
        ]
    }


@router.get("/today", response_model=dict)
async def get_today_tasks(
    current_user: User = require_permission("followup:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取今日待办任务（需要followup:read权限，自动数据隔离）"""
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    query = select(FollowUp).where(
        FollowUp.next_date >= today,
        FollowUp.next_date < tomorrow
    )
    # 数据隔离过滤
    query = filter_by_organization(query, FollowUp, current_user)
    query = query.order_by(FollowUp.next_date)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "date": today,
        "total": len(tasks),
        "items": [
            {
                "id": t.id,
                "customer_id": t.customer_id,
                "customer_name": t.customer_name,
                "next_action": t.next_action,
                "next_date": t.next_date,
                "ai_script": t.ai_script
            }
            for t in tasks
        ]
    }


@router.get("/upcoming", response_model=dict)
async def get_upcoming_tasks(
    days: int = 7,
    current_user: User = require_permission("followup:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取即将到来的任务（需要followup:read权限，自动数据隔离）"""
    today = datetime.now().date()
    end_date = today + timedelta(days=days)
    
    query = select(FollowUp).where(
        FollowUp.next_date >= today,
        FollowUp.next_date < end_date
    )
    # 数据隔离过滤
    query = filter_by_organization(query, FollowUp, current_user)
    query = query.order_by(FollowUp.next_date)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "start_date": today,
        "end_date": end_date,
        "total": len(tasks),
        "items": [
            {
                "id": t.id,
                "customer_id": t.customer_id,
                "customer_name": t.customer_name,
                "next_action": t.next_action,
                "next_date": t.next_date
            }
            for t in tasks
        ]
    }


@router.delete("/{follow_up_id}", response_model=dict)
async def delete_follow_up(
    follow_up_id: int,
    current_user: User = require_permission("followup:delete"),
    db: AsyncSession = Depends(get_db)
):
    """删除跟进记录（需要followup:delete权限和数据访问权限）"""
    follow_up = await check_data_access(db, current_user, FollowUp, follow_up_id)
    
    await db.delete(follow_up)
    await db.commit()
    
    return {"message": "跟进记录删除成功"}
