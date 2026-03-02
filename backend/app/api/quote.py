from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_permission, filter_by_organization, check_data_access
from app.models.models import Quote, QuoteStatus, User
from app.schemas.schemas import QuoteCreate, QuoteUpdate

router = APIRouter()


@router.post("/", response_model=dict)
async def create_quote(
    quote_data: QuoteCreate,
    current_user: User = require_permission("quote:write"),
    db: AsyncSession = Depends(get_db)
):
    """创建报价单（需要quote:write权限）"""
    total_amount = sum(
        item.quantity * item.unit_price 
        for item in quote_data.items
    )
    
    items_data = [item.model_dump() for item in quote_data.items]
    
    quote = Quote(
        customer_id=quote_data.customer_id,
        customer_name=quote_data.customer_name,
        opportunity_id=quote_data.opportunity_id,
        items=items_data,
        total_amount=total_amount,
        status=QuoteStatus.DRAFT.value,
        valid_until=quote_data.valid_until,
        remark=quote_data.remark,
        # 数据隔离字段
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    
    return {
        "id": quote.id,
        "total_amount": quote.total_amount,
        "status": quote.status,
        "created_at": quote.created_at,
        "message": "报价单创建成功"
    }


@router.get("/", response_model=dict)
async def list_quotes(
    page: int = 1,
    size: int = 20,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    current_user: User = require_permission("quote:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取报价单列表（需要quote:read权限，自动数据隔离）"""
    query = select(Quote)
    
    # 数据隔离过滤
    query = filter_by_organization(query, Quote, current_user)
    
    if status:
        query = query.where(Quote.status == status)
    
    if customer_id:
        query = query.where(Quote.customer_id == customer_id)
    
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    query = query.offset((page - 1) * size).limit(size).order_by(Quote.created_at.desc())
    result = await db.execute(query)
    quotes = result.scalars().all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": q.id,
                "customer_id": q.customer_id,
                "customer_name": q.customer_name,
                "total_amount": q.total_amount,
                "status": q.status,
                "valid_until": q.valid_until,
                "created_at": q.created_at
            }
            for q in quotes
        ]
    }


@router.get("/{quote_id}", response_model=dict)
async def get_quote(
    quote_id: int,
    current_user: User = require_permission("quote:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取报价单详情（需要quote:read权限和数据访问权限）"""
    quote = await check_data_access(db, current_user, Quote, quote_id)
    
    return {
        "id": quote.id,
        "customer_id": quote.customer_id,
        "customer_name": quote.customer_name,
        "opportunity_id": quote.opportunity_id,
        "items": quote.items,
        "total_amount": quote.total_amount,
        "status": quote.status,
        "ai_price_suggestion": quote.ai_price_suggestion,
        "valid_until": quote.valid_until,
        "remark": quote.remark,
        "created_at": quote.created_at,
        "updated_at": quote.updated_at
    }


@router.put("/{quote_id}", response_model=dict)
async def update_quote(
    quote_id: int,
    quote_data: QuoteUpdate,
    current_user: User = require_permission("quote:write"),
    db: AsyncSession = Depends(get_db)
):
    """更新报价单（需要quote:write权限和数据访问权限）"""
    quote = await check_data_access(db, current_user, Quote, quote_id)
    
    if quote_data.items:
        quote.items = [item.model_dump() for item in quote_data.items]
        quote.total_amount = sum(
            item.quantity * item.unit_price 
            for item in quote_data.items
        )
    
    if quote_data.status:
        quote.status = quote_data.status
    
    if quote_data.valid_until:
        quote.valid_until = quote_data.valid_until
    
    if quote_data.remark:
        quote.remark = quote_data.remark
    
    await db.commit()
    await db.refresh(quote)
    
    return {
        "id": quote.id,
        "total_amount": quote.total_amount,
        "message": "报价单更新成功"
    }


@router.delete("/{quote_id}", response_model=dict)
async def delete_quote(
    quote_id: int,
    current_user: User = require_permission("quote:delete"),
    db: AsyncSession = Depends(get_db)
):
    """删除报价单（需要quote:delete权限和数据访问权限）"""
    quote = await check_data_access(db, current_user, Quote, quote_id)
    
    await db.delete(quote)
    await db.commit()
    
    return {"message": "报价单删除成功"}


@router.post("/{quote_id}/send", response_model=dict)
async def send_quote(
    quote_id: int,
    current_user: User = require_permission("quote:write"),
    db: AsyncSession = Depends(get_db)
):
    """发送报价单（需要quote:write权限和数据访问权限）"""
    quote = await check_data_access(db, current_user, Quote, quote_id)
    
    quote.status = QuoteStatus.SENT.value
    await db.commit()
    
    return {
        "id": quote.id,
        "status": quote.status,
        "message": "报价单已发送"
    }
