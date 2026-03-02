from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.models import Customer, Opportunity, Quote, FollowUp
from app.services.ai_service import ai_service

router = APIRouter()


@router.get("/overview", response_model=dict)
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    获取数据分析概览
    """
    today = datetime.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    total_customers = await db.execute(select(func.count()).select_from(Customer))
    total_customers = total_customers.scalar() or 0
    
    new_customers_month = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.created_at >= month_start)
    )
    new_customers_month = new_customers_month.scalar() or 0
    
    new_customers_year = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.created_at >= year_start)
    )
    new_customers_year = new_customers_year.scalar() or 0
    
    total_opportunities = await db.execute(select(func.count()).select_from(Opportunity))
    total_opportunities = total_opportunities.scalar() or 0
    
    total_amount = await db.execute(select(func.sum(Opportunity.amount)).select_from(Opportunity))
    total_amount = total_amount.scalar() or 0
    
    won_amount = await db.execute(
        select(func.sum(Opportunity.amount)).select_from(Opportunity).where(Opportunity.stage == 'closed_won')
    )
    won_amount = won_amount.scalar() or 0
    
    month_amount = await db.execute(
        select(func.sum(Opportunity.amount)).select_from(Opportunity).where(
            Opportunity.created_at >= month_start
        )
    )
    month_amount = month_amount.scalar() or 0
    
    won_count = await db.execute(
        select(func.count()).select_from(Opportunity).where(Opportunity.stage == 'closed_won')
    )
    won_count = won_count.scalar() or 0
    
    lost_count = await db.execute(
        select(func.count()).select_from(Opportunity).where(Opportunity.stage == 'closed_lost')
    )
    lost_count = lost_count.scalar() or 0
    
    total_closed = won_count + lost_count
    conversion_rate = (won_count / total_closed * 100) if total_closed > 0 else 0
    
    return {
        "customers": {
            "total": total_customers,
            "new_this_month": new_customers_month,
            "new_this_year": new_customers_year
        },
        "opportunities": {
            "total": total_opportunities,
            "total_amount": total_amount,
            "won_amount": won_amount,
            "month_amount": month_amount
        },
        "conversion": {
            "won_count": won_count,
            "lost_count": lost_count,
            "conversion_rate": round(conversion_rate, 1)
        }
    }


@router.get("/customer-trend", response_model=dict)
async def get_customer_trend(
    months: int = 6,
    db: AsyncSession = Depends(get_db)
):
    """
    获取客户增长趋势
    """
    today = datetime.now().date()
    trend_data = []
    
    for i in range(months - 1, -1, -1):
        month_date = today - timedelta(days=i * 30)
        month_start = month_date.replace(day=1)
        
        if month_date.month == 12:
            next_month = month_date.replace(year=month_date.year + 1, month=1, day=1)
        else:
            next_month = month_date.replace(month=month_date.month + 1, day=1)
        
        count = await db.execute(
            select(func.count()).select_from(Customer).where(
                and_(Customer.created_at >= month_start, Customer.created_at < next_month)
            )
        )
        count = count.scalar() or 0
        
        trend_data.append({
            "month": month_start.strftime("%Y-%m"),
            "new_customers": count
        })
    
    return {"trend": trend_data}


@router.get("/sales-trend", response_model=dict)
async def get_sales_trend(
    months: int = 6,
    db: AsyncSession = Depends(get_db)
):
    """
    获取销售趋势
    """
    today = datetime.now().date()
    trend_data = []
    
    for i in range(months - 1, -1, -1):
        month_date = today - timedelta(days=i * 30)
        month_start = month_date.replace(day=1)
        
        if month_date.month == 12:
            next_month = month_date.replace(year=month_date.year + 1, month=1, day=1)
        else:
            next_month = month_date.replace(month=month_date.month + 1, day=1)
        
        amount = await db.execute(
            select(func.sum(Opportunity.amount)).select_from(Opportunity).where(
                and_(Opportunity.stage == 'closed_won', 
                     Opportunity.created_at >= month_start, 
                     Opportunity.created_at < next_month)
            )
        )
        amount = amount.scalar() or 0
        
        count = await db.execute(
            select(func.count()).select_from(Opportunity).where(
                and_(Opportunity.stage == 'closed_won',
                     Opportunity.created_at >= month_start,
                     Opportunity.created_at < next_month)
            )
        )
        count = count.scalar() or 0
        
        trend_data.append({
            "month": month_start.strftime("%Y-%m"),
            "amount": amount,
            "deals": count
        })
    
    return {"trend": trend_data}


@router.get("/industry-distribution", response_model=dict)
async def get_industry_distribution(
    db: AsyncSession = Depends(get_db)
):
    """
    获取客户行业分布
    """
    result = await db.execute(
        select(Customer.industry, func.count().label('count')).group_by(Customer.industry)
    )
    
    distribution = []
    for row in result:
        if row.industry:
            distribution.append({
                "industry": row.industry,
                "count": row.count
            })
    
    return {"distribution": distribution}


@router.get("/source-distribution", response_model=dict)
async def get_source_distribution(
    db: AsyncSession = Depends(get_db)
):
    """
    获取客户来源分布
    """
    result = await db.execute(
        select(Customer.source, func.count().label('count')).group_by(Customer.source)
    )
    
    distribution = []
    for row in result:
        if row.source:
            distribution.append({
                "source": row.source,
                "count": row.count
            })
    
    return {"distribution": distribution}


@router.get("/stage-conversion", response_model=dict)
async def get_stage_conversion(
    db: AsyncSession = Depends(get_db)
):
    """
    获取销售漏斗各阶段转化率
    """
    stages = ['initial', 'need_confirm', 'quoting', 'negotiating', 'closed_won', 'closed_lost']
    stage_names = {
        'initial': '初步接触',
        'need_confirm': '需求确认',
        'quoting': '报价中',
        'negotiating': '谈判中',
        'closed_won': '成交',
        'closed_lost': '失败'
    }
    
    result = await db.execute(
        select(Opportunity.stage, func.count().label('count'), func.sum(Opportunity.amount).label('amount'))
        .group_by(Opportunity.stage)
    )
    
    stage_data = {}
    for row in result:
        stage_data[row.stage] = {
            "count": row.count,
            "amount": row.amount or 0
        }
    
    funnel = []
    for stage in stages:
        data = stage_data.get(stage, {"count": 0, "amount": 0})
        funnel.append({
            "stage": stage,
            "stage_name": stage_names[stage],
            "count": data["count"],
            "amount": data["amount"]
        })
    
    return {"funnel": funnel}


@router.get("/top-customers", response_model=dict)
async def get_top_customers(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    获取成交金额最高的客户
    """
    result = await db.execute(
        select(
            Opportunity.customer_id,
            Opportunity.customer_name,
            func.sum(Opportunity.amount).label('total_amount'),
            func.count().label('deal_count')
        )
        .where(Opportunity.stage == 'closed_won')
        .group_by(Opportunity.customer_id, Opportunity.customer_name)
        .order_by(func.sum(Opportunity.amount).desc())
        .limit(limit)
    )
    
    top_customers = []
    for row in result:
        top_customers.append({
            "customer_id": row.customer_id,
            "customer_name": row.customer_name,
            "total_amount": row.total_amount,
            "deal_count": row.deal_count
        })
    
    return {"top_customers": top_customers}


@router.get("/ai-forecast", response_model=dict)
async def get_ai_forecast(
    db: AsyncSession = Depends(get_db)
):
    """
    AI销售预测
    """
    overview = await get_analytics_overview(db)
    trend = await get_sales_trend(6, db)
    funnel = await get_stage_conversion(db)
    
    opportunities = await db.execute(
        select(Opportunity).where(Opportunity.stage.not_in(['closed_won', 'closed_lost']))
    )
    pipeline = [
        {
            "id": o.id,
            "name": o.name,
            "amount": o.amount,
            "stage": o.stage,
            "probability": o.probability
        }
        for o in opportunities.scalars().all()
    ]
    
    forecast = await ai_service.sales_forecast(overview, pipeline)
    
    return {
        "historical_data": overview,
        "pipeline": pipeline,
        "forecast": forecast
    }


@router.get("/ai-recommendation", response_model=dict)
async def get_ai_recommendation(
    db: AsyncSession = Depends(get_db)
):
    """
    AI智能推荐
    """
    today_tasks = await db.execute(
        select(FollowUp).where(FollowUp.next_date >= datetime.now().date())
    )
    
    customers = await db.execute(select(Customer).limit(20))
    customers_list = [
        {"id": c.id, "name": c.name, "status": c.status, "company": c.company}
        for c in customers.scalars().all()
    ]
    
    opportunities = await db.execute(
        select(Opportunity).where(Opportunity.stage.not_in(['closed_won', 'closed_lost']))
    )
    opportunities_list = [
        {"id": o.id, "name": o.name, "amount": o.amount, "stage": o.stage}
        for o in opportunities.scalars().all()
    ]
    
    user_context = {
        "today_tasks": len(today_tasks.scalars().all()),
        "total_customers": len(customers_list),
        "active_opportunities": len(opportunities_list)
    }
    
    recommendation = await ai_service.smart_recommendation(user_context, customers_list, opportunities_list)
    
    return {
        "user_context": user_context,
        "recommendation": recommendation
    }


@router.get("/ai-report", response_model=dict)
async def get_ai_report(
    period: str = "本周",
    db: AsyncSession = Depends(get_db)
):
    """
    AI生成销售报告
    """
    overview = await get_analytics_overview(db)
    trend = await get_sales_trend(3, db)
    
    stats = {
        **overview,
        "trend": trend["trend"]
    }
    
    report = await ai_service.generate_sales_report(stats, period)
    
    return {
        "period": period,
        "stats": stats,
        "report": report
    }


@router.get("/lost-analysis", response_model=dict)
async def get_lost_analysis(
    db: AsyncSession = Depends(get_db)
):
    """
    丢单原因分析
    """
    lost_opportunities = await db.execute(
        select(Opportunity).where(Opportunity.stage == 'closed_lost')
    )
    
    lost_list = [
        {
            "id": o.id,
            "name": o.name,
            "amount": o.amount,
            "customer_name": o.customer_name,
            "remark": o.remark
        }
        for o in lost_opportunities.scalars().all()
    ]
    
    analysis = await ai_service.analyze_lost_reason(lost_list)
    
    return {
        "total_lost": len(lost_list),
        "total_amount": sum(o["amount"] or 0 for o in lost_list),
        "analysis": analysis
    }
