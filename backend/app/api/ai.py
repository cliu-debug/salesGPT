from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_permission, check_data_access
from app.models.models import Customer, Opportunity, FollowUp, User
from app.services.ai_service import ai_service

router = APIRouter()


@router.post("/customer-profile/{customer_id}", response_model=dict)
async def analyze_customer_profile(
    customer_id: int,
    current_user: User = require_permission("ai:analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    AI分析客户画像（需要ai:analyze权限和数据访问权限）
    """
    # 检查数据访问权限
    customer = await check_data_access(db, current_user, Customer, customer_id)
    
    follow_ups_query = select(FollowUp).where(
        FollowUp.customer_id == customer_id
    ).order_by(FollowUp.created_at.desc()).limit(10)
    follow_ups_result = await db.execute(follow_ups_query)
    history = [
        {
            "content": f.content,
            "created_at": f.created_at
        }
        for f in follow_ups_result.scalars().all()
    ]
    
    customer_info = {
        "name": customer.name,
        "company": customer.company,
        "industry": customer.industry,
        "source": customer.source,
        "status": customer.status,
        "remark": customer.remark
    }
    
    profile = await ai_service.analyze_customer(customer_info, history)
    
    customer.ai_profile = profile
    await db.commit()
    
    return {
        "customer_id": customer_id,
        "profile": profile
    }


@router.post("/quote-suggestion/{quote_id}", response_model=dict)
async def get_quote_suggestion(
    quote_id: int,
    current_user: User = require_permission("ai:analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    AI报价建议（需要ai:analyze权限和数据访问权限）
    """
    from app.models.models import Quote
    
    # 检查数据访问权限
    quote = await check_data_access(db, current_user, Quote, quote_id)
    
    customer_query = select(Customer).where(Customer.id == quote.customer_id)
    customer_result = await db.execute(customer_query)
    customer = customer_result.scalar_one_or_none()
    
    customer_info = {
        "name": customer.name if customer else "未知",
        "company": customer.company if customer else "未知",
        "industry": customer.industry if customer else "未知"
    }
    
    suggestion = await ai_service.suggest_quote_price(
        customer_info,
        quote.items or []
    )
    
    quote.ai_price_suggestion = suggestion
    await db.commit()
    
    return {
        "quote_id": quote_id,
        "suggestion": suggestion
    }


@router.post("/follow-up-script/{customer_id}", response_model=dict)
async def generate_follow_up_script(
    customer_id: int,
    purpose: str = "日常跟进",
    current_user: User = require_permission("ai:analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    AI生成跟进话术（需要ai:analyze权限和数据访问权限）
    """
    # 检查数据访问权限
    customer = await check_data_access(db, current_user, Customer, customer_id)
    
    from app.models.models import FollowUp
    follow_ups_query = select(FollowUp).where(
        FollowUp.customer_id == customer_id
    ).order_by(FollowUp.created_at.desc()).limit(5)
    follow_ups_result = await db.execute(follow_ups_query)
    history = [
        {"content": f.content, "created_at": str(f.created_at)}
        for f in follow_ups_result.scalars().all()
    ]
    
    customer_info = {
        "name": customer.name,
        "company": customer.company,
        "industry": customer.industry,
        "status": customer.status
    }
    
    script = await ai_service.generate_follow_up_script(
        customer_info,
        history,
        purpose
    )
    
    return {
        "customer_id": customer_id,
        "purpose": purpose,
        "script": script
    }


@router.post("/close-probability/{opportunity_id}", response_model=dict)
async def predict_close_probability(
    opportunity_id: int,
    current_user: User = require_permission("ai:analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    AI预测成交概率（需要ai:analyze权限和数据访问权限）
    """
    # 检查数据访问权限
    opportunity = await check_data_access(db, current_user, Opportunity, opportunity_id)
    
    customer_info = None
    if opportunity.customer_id:
        customer_query = select(Customer).where(Customer.id == opportunity.customer_id)
        customer_result = await db.execute(customer_query)
        customer = customer_result.scalar_one_or_none()
        if customer:
            customer_info = {
                "name": customer.name,
                "company": customer.company,
                "industry": customer.industry,
                "status": customer.status
            }
    
    opportunity_info = {
        "name": opportunity.name,
        "amount": opportunity.amount,
        "stage": opportunity.stage,
        "expected_date": str(opportunity.expected_date) if opportunity.expected_date else None
    }
    
    prediction = await ai_service.predict_close_probability(
        opportunity_info,
        customer_info
    )
    
    if "probability" in prediction:
        opportunity.probability = prediction["probability"]
        opportunity.ai_suggestion = prediction
        await db.commit()
    
    return {
        "opportunity_id": opportunity_id,
        "prediction": prediction
    }
