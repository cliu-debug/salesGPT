from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_permission, filter_by_organization
from app.models.models import Customer, Opportunity, Quote, FollowUp, User
from app.services.ai_service import ai_service

router = APIRouter()


@router.get("/", response_model=dict)
async def get_dashboard(
    current_user: User = require_permission("dashboard:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取仪表盘数据（需要dashboard:read权限，自动数据隔离）
    """
    # 客户统计（数据隔离）
    total_customers_query = select(func.count()).select_from(Customer)
    total_customers_query = filter_by_organization(total_customers_query, Customer, current_user)
    total_customers_result = await db.execute(total_customers_query)
    total_customers = total_customers_result.scalar()
    
    month_ago = datetime.now() - timedelta(days=30)
    new_customers_query = select(func.count()).select_from(Customer).where(
        Customer.created_at >= month_ago
    )
    new_customers_query = filter_by_organization(new_customers_query, Customer, current_user)
    new_customers_result = await db.execute(new_customers_query)
    new_customers = new_customers_result.scalar()
    
    # 机会统计（数据隔离）
    total_opportunities_query = select(func.count()).select_from(Opportunity)
    total_opportunities_query = filter_by_organization(total_opportunities_query, Opportunity, current_user)
    total_opportunities_result = await db.execute(total_opportunities_query)
    total_opportunities = total_opportunities_result.scalar()
    
    total_amount_query = select(func.sum(Opportunity.amount)).select_from(Opportunity)
    total_amount_query = filter_by_organization(total_amount_query, Opportunity, current_user)
    total_amount_result = await db.execute(total_amount_query)
    total_amount = total_amount_result.scalar() or 0
    
    won_amount_query = select(func.sum(Opportunity.amount)).select_from(Opportunity).where(
        Opportunity.stage == "closed_won"
    )
    won_amount_query = filter_by_organization(won_amount_query, Opportunity, current_user)
    won_amount_result = await db.execute(won_amount_query)
    won_amount = won_amount_result.scalar() or 0
    
    total_opps_for_rate = select(func.count()).select_from(Opportunity).where(
        Opportunity.stage.in_(["closed_won", "closed_lost"])
    )
    total_opps_for_rate = filter_by_organization(total_opps_for_rate, Opportunity, current_user)
    total_closed_result = await db.execute(total_opps_for_rate)
    total_closed = total_closed_result.scalar() or 1
    
    won_count_query = select(func.count()).select_from(Opportunity).where(
        Opportunity.stage == "closed_won"
    )
    won_count_query = filter_by_organization(won_count_query, Opportunity, current_user)
    won_count_result = await db.execute(won_count_query)
    won_count = won_count_result.scalar() or 0
    
    conversion_rate = (won_count / total_closed * 100) if total_closed > 0 else 0
    
    # 阶段分布（数据隔离）
    stage_query = select(
        Opportunity.stage,
        func.count().label('count'),
        func.sum(Opportunity.amount).label('amount')
    )
    stage_query = filter_by_organization(stage_query, Opportunity, current_user)
    stage_query = stage_query.group_by(Opportunity.stage)
    
    stage_result = await db.execute(stage_query)
    stage_distribution = {}
    for row in stage_result:
        stage_distribution[row.stage] = {
            "count": row.count,
            "amount": row.amount or 0
        }
    
    # 最近客户（数据隔离）
    recent_customers_query = select(Customer)
    recent_customers_query = filter_by_organization(recent_customers_query, Customer, current_user)
    recent_customers_query = recent_customers_query.order_by(
        Customer.created_at.desc()
    ).limit(5)
    recent_customers_result = await db.execute(recent_customers_query)
    recent_customers = [
        {
            "id": c.id,
            "name": c.name,
            "company": c.company,
            "status": c.status,
            "created_at": c.created_at
        }
        for c in recent_customers_result.scalars().all()
    ]
    
    # 最近机会（数据隔离）
    recent_opportunities_query = select(Opportunity)
    recent_opportunities_query = filter_by_organization(recent_opportunities_query, Opportunity, current_user)
    recent_opportunities_query = recent_opportunities_query.order_by(
        Opportunity.created_at.desc()
    ).limit(5)
    recent_opportunities_result = await db.execute(recent_opportunities_query)
    recent_opportunities = [
        {
            "id": o.id,
            "name": o.name,
            "customer_name": o.customer_name,
            "amount": o.amount,
            "stage": o.stage,
            "created_at": o.created_at
        }
        for o in recent_opportunities_result.scalars().all()
    ]
    
    return {
        "total_customers": total_customers,
        "new_customers_this_month": new_customers,
        "total_opportunities": total_opportunities,
        "total_amount": total_amount,
        "won_amount": won_amount,
        "conversion_rate": round(conversion_rate, 1),
        "stage_distribution": stage_distribution,
        "recent_customers": recent_customers,
        "recent_opportunities": recent_opportunities
    }


@router.get("/ai-insights", response_model=dict)
async def get_ai_insights(
    current_user: User = require_permission("dashboard:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取AI销售洞察（需要dashboard:read权限）
    """
    dashboard_data = await get_dashboard(current_user, db)
    
    insights = await ai_service.get_sales_insights(dashboard_data)
    
    return {
        "insights": insights,
        "generated_at": datetime.now()
    }


@router.get("/today-tasks", response_model=dict)
async def get_today_tasks(
    current_user: User = require_permission("dashboard:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取今日待办（需要dashboard:read权限，自动数据隔离）
    """
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    follow_ups_query = select(FollowUp).where(
        FollowUp.next_date >= today,
        FollowUp.next_date < tomorrow
    )
    # 数据隔离过滤
    follow_ups_query = filter_by_organization(follow_ups_query, FollowUp, current_user)
    follow_ups_query = follow_ups_query.order_by(FollowUp.next_date)
    
    result = await db.execute(follow_ups_query)
    tasks = result.scalars().all()
    
    return {
        "date": today,
        "total": len(tasks),
        "tasks": [
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
