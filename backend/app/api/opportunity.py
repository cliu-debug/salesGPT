from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_permission, filter_by_organization, check_data_access
from app.models.models import Opportunity, OpportunityStage, User
from app.schemas.schemas import OpportunityCreate, OpportunityUpdate, OpportunityResponse

router = APIRouter()


@router.post("/", response_model=dict)
async def create_opportunity(
    opportunity_data: OpportunityCreate,
    current_user: User = require_permission("opportunity:write"),
    db: AsyncSession = Depends(get_db)
):
    """创建销售机会（需要opportunity:write权限）"""
    opportunity = Opportunity(
        customer_id=opportunity_data.customer_id,
        customer_name=opportunity_data.customer_name,
        name=opportunity_data.name,
        amount=opportunity_data.amount or 0,
        stage=opportunity_data.stage or OpportunityStage.INITIAL.value,
        expected_date=opportunity_data.expected_date,
        remark=opportunity_data.remark,
        # 数据隔离字段
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )
    db.add(opportunity)
    await db.commit()
    await db.refresh(opportunity)
    
    return {
        "id": opportunity.id,
        "name": opportunity.name,
        "amount": opportunity.amount,
        "stage": opportunity.stage,
        "created_at": opportunity.created_at,
        "message": "销售机会创建成功"
    }


@router.get("/", response_model=dict)
async def list_opportunities(
    page: int = 1,
    size: int = 20,
    stage: Optional[str] = None,
    customer_id: Optional[int] = None,
    current_user: User = require_permission("opportunity:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取销售机会列表（需要opportunity:read权限，自动数据隔离）"""
    query = select(Opportunity)
    
    # 数据隔离过滤
    query = filter_by_organization(query, Opportunity, current_user)
    
    if stage:
        query = query.where(Opportunity.stage == stage)
    
    if customer_id:
        query = query.where(Opportunity.customer_id == customer_id)
    
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    query = query.offset((page - 1) * size).limit(size).order_by(Opportunity.created_at.desc())
    result = await db.execute(query)
    opportunities = result.scalars().all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": o.id,
                "customer_id": o.customer_id,
                "customer_name": o.customer_name,
                "name": o.name,
                "amount": o.amount,
                "stage": o.stage,
                "probability": o.probability,
                "expected_date": o.expected_date,
                "created_at": o.created_at
            }
            for o in opportunities
        ]
    }


@router.get("/{opportunity_id}", response_model=dict)
async def get_opportunity(
    opportunity_id: int,
    current_user: User = require_permission("opportunity:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取销售机会详情（需要opportunity:read权限和数据访问权限）"""
    opportunity = await check_data_access(db, current_user, Opportunity, opportunity_id)
    
    return {
        "id": opportunity.id,
        "customer_id": opportunity.customer_id,
        "customer_name": opportunity.customer_name,
        "name": opportunity.name,
        "amount": opportunity.amount,
        "stage": opportunity.stage,
        "probability": opportunity.probability,
        "expected_date": opportunity.expected_date,
        "ai_suggestion": opportunity.ai_suggestion,
        "remark": opportunity.remark,
        "created_at": opportunity.created_at,
        "updated_at": opportunity.updated_at
    }


@router.put("/{opportunity_id}", response_model=dict)
async def update_opportunity(
    opportunity_id: int,
    opportunity_data: OpportunityUpdate,
    current_user: User = require_permission("opportunity:write"),
    db: AsyncSession = Depends(get_db)
):
    """更新销售机会（需要opportunity:write权限和数据访问权限）"""
    opportunity = await check_data_access(db, current_user, Opportunity, opportunity_id)
    
    update_data = opportunity_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(opportunity, key, value)
    
    # 根据阶段自动更新概率
    stage_probability_map = {
        "won": 100,
        "closed_won": 100,
        "lost": 0,
        "closed_lost": 0,
        "initial": 20,
        "need_confirm": 30,
        "quoting": 50,
        "negotiation": 70,
        "negotiating": 70
    }
    
    if opportunity.stage in stage_probability_map:
        # 如果没有显式设置概率，则自动更新
        if "probability" not in update_data:
            opportunity.probability = stage_probability_map[opportunity.stage]
    
    await db.commit()
    await db.refresh(opportunity)
    
    return {
        "id": opportunity.id,
        "customer_id": opportunity.customer_id,
        "customer_name": opportunity.customer_name,
        "name": opportunity.name,
        "amount": opportunity.amount,
        "stage": opportunity.stage,
        "probability": opportunity.probability,
        "expected_date": opportunity.expected_date,
        "ai_suggestion": opportunity.ai_suggestion,
        "remark": opportunity.remark,
        "created_at": opportunity.created_at,
        "updated_at": opportunity.updated_at,
        "message": "销售机会更新成功"
    }


@router.delete("/{opportunity_id}", response_model=dict)
async def delete_opportunity(
    opportunity_id: int,
    current_user: User = require_permission("opportunity:delete"),
    db: AsyncSession = Depends(get_db)
):
    """删除销售机会（需要opportunity:delete权限和数据访问权限）"""
    opportunity = await check_data_access(db, current_user, Opportunity, opportunity_id)
    
    await db.delete(opportunity)
    await db.commit()
    
    return {"message": "销售机会删除成功"}


@router.get("/stats/funnel", response_model=dict)
async def get_funnel_stats(
    current_user: User = require_permission("opportunity:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取销售漏斗统计（需要opportunity:read权限，自动数据隔离）"""
    query = select(Opportunity.stage, func.count().label('count'), func.sum(Opportunity.amount).label('total_amount'))
    # 数据隔离过滤
    query = filter_by_organization(query, Opportunity, current_user)
    query = query.group_by(Opportunity.stage)
    
    result = await db.execute(query)
    stages = result.all()
    
    funnel_data = {}
    for stage in stages:
        funnel_data[stage.stage] = {
            "count": stage.count,
            "total_amount": float(stage.total_amount or 0)
        }
    
    return funnel_data
