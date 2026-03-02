from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_permission, filter_by_organization, check_data_access
from app.models.models import Customer, CustomerStatus, User
from app.schemas.schemas import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter()


@router.post("/", response_model=dict)
async def create_customer(
    customer_data: CustomerCreate,
    current_user: User = require_permission("customer:write"),
    db: AsyncSession = Depends(get_db)
):
    """创建客户（需要customer:write权限）"""
    customer = Customer(
        name=customer_data.name,
        contact=customer_data.contact,
        phone=customer_data.phone,
        email=customer_data.email,
        company=customer_data.company,
        industry=customer_data.industry,
        source=customer_data.source,
        status=customer_data.status or CustomerStatus.POTENTIAL.value,
        tags=customer_data.tags,
        remark=customer_data.remark,
        # 数据隔离字段
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    
    return {
        "id": customer.id,
        "name": customer.name,
        "contact": customer.contact,
        "phone": customer.phone,
        "email": customer.email,
        "company": customer.company,
        "industry": customer.industry,
        "source": customer.source,
        "status": customer.status,
        "tags": customer.tags,
        "remark": customer.remark,
        "created_at": customer.created_at,
        "message": "客户创建成功"
    }


@router.get("/", response_model=dict)
async def list_customers(
    page: int = 1,
    size: int = 20,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    current_user: User = require_permission("customer:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取客户列表（需要customer:read权限，自动数据隔离）"""
    query = select(Customer)
    
    # 数据隔离过滤
    query = filter_by_organization(query, Customer, current_user)
    
    if status:
        query = query.where(Customer.status == status)
    
    if keyword:
        query = query.where(
            or_(
                Customer.name.contains(keyword),
                Customer.company.contains(keyword),
                Customer.phone.contains(keyword)
            )
        )
    
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    query = query.offset((page - 1) * size).limit(size).order_by(Customer.created_at.desc())
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "contact": c.contact,
                "phone": c.phone,
                "company": c.company,
                "industry": c.industry,
                "status": c.status,
                "tags": c.tags,
                "created_at": c.created_at
            }
            for c in customers
        ]
    }


@router.get("/{customer_id}", response_model=dict)
async def get_customer(
    customer_id: int,
    current_user: User = require_permission("customer:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取客户详情（需要customer:read权限和数据访问权限）"""
    # 检查数据访问权限
    customer = await check_data_access(db, current_user, Customer, customer_id)
    
    return {
        "id": customer.id,
        "name": customer.name,
        "contact": customer.contact,
        "phone": customer.phone,
        "email": customer.email,
        "company": customer.company,
        "industry": customer.industry,
        "source": customer.source,
        "status": customer.status,
        "tags": customer.tags,
        "ai_profile": customer.ai_profile,
        "remark": customer.remark,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at
    }


@router.put("/{customer_id}", response_model=dict)
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    current_user: User = require_permission("customer:write"),
    db: AsyncSession = Depends(get_db)
):
    """更新客户信息（需要customer:write权限和数据访问权限）"""
    # 检查数据访问权限
    customer = await check_data_access(db, current_user, Customer, customer_id)
    
    update_data = customer_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(customer, key, value)
    
    await db.commit()
    await db.refresh(customer)
    
    return {
        "id": customer.id,
        "name": customer.name,
        "contact": customer.contact,
        "phone": customer.phone,
        "email": customer.email,
        "company": customer.company,
        "industry": customer.industry,
        "source": customer.source,
        "status": customer.status,
        "tags": customer.tags,
        "remark": customer.remark,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "message": "客户更新成功"
    }


@router.delete("/{customer_id}", response_model=dict)
async def delete_customer(
    customer_id: int,
    current_user: User = require_permission("customer:delete"),
    db: AsyncSession = Depends(get_db)
):
    """删除客户（需要customer:delete权限和数据访问权限）"""
    # 检查数据访问权限
    customer = await check_data_access(db, current_user, Customer, customer_id)
    
    await db.delete(customer)
    await db.commit()
    
    return {"message": "客户删除成功"}


@router.get("/stats/summary", response_model=dict)
async def get_customer_stats(
    current_user: User = require_permission("customer:read"),
    db: AsyncSession = Depends(get_db)
):
    """获取客户统计（需要customer:read权限，自动数据隔离）"""
    query = select(Customer)
    # 数据隔离过滤
    query = filter_by_organization(query, Customer, current_user)
    
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()
    
    status_query = select(Customer.status, func.count().label('count'))
    status_query = filter_by_organization(status_query, Customer, current_user)
    status_query = status_query.group_by(Customer.status)
    status_result = await db.execute(status_query)
    status_distribution = {row.status: row.count for row in status_result}
    
    month_ago = datetime.now() - timedelta(days=30)
    new_query = select(func.count()).select_from(Customer).where(Customer.created_at >= month_ago)
    new_query = filter_by_organization(new_query, Customer, current_user)
    new_result = await db.execute(new_query)
    new_customers = new_result.scalar()
    
    return {
        "total": total,
        "new_this_month": new_customers,
        "status_distribution": status_distribution
    }
