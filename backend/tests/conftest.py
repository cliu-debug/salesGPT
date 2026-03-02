"""
测试配置文件 - fixtures和测试工具
"""
import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.core.auth import hash_password, create_access_token
from app.models.models import (
    User, Role, Organization, Team, Customer, 
    Opportunity, Quote, FollowUp, AgentTask
)


# 测试数据库URL (使用内存SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ========== 测试数据库配置 ==========

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# ========== 测试数据fixtures ==========

@pytest_asyncio.fixture(scope="function")
async def test_organization(db_session: AsyncSession) -> Organization:
    """创建测试组织"""
    org = Organization(
        name="测试科技有限公司",
        plan="pro",
        settings={"max_users": 10}
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture(scope="function")
async def test_team(db_session: AsyncSession, test_organization: Organization) -> Team:
    """创建测试团队"""
    team = Team(
        name="销售一部",
        organization_id=test_organization.id
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture(scope="function")
async def test_roles(db_session: AsyncSession, test_organization: Organization) -> dict:
    """创建测试角色"""
    from app.core.permissions import DEFAULT_PERMISSIONS
    
    roles = {}
    for role_code, permissions in DEFAULT_PERMISSIONS.items():
        role = Role(
            name=role_code.replace("_", " ").title(),
            code=role_code,
            permissions=permissions,
            organization_id=test_organization.id
        )
        db_session.add(role)
        roles[role_code] = role
    
    await db_session.commit()
    
    for code, role in roles.items():
        await db_session.refresh(role)
    
    return roles


@pytest_asyncio.fixture(scope="function")
async def test_superuser(
    db_session: AsyncSession, 
    test_organization: Organization,
    test_team: Team,
    test_roles: dict
) -> User:
    """创建超级管理员用户"""
    user = User(
        username="superadmin",
        email="superadmin@test.com",
        password_hash=hash_password("password123"),
        full_name="超级管理员",
        role_id=test_roles["super_admin"].id,
        team_id=test_team.id,
        organization_id=test_organization.id,
        is_active=True,
        is_superuser=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_admin_user(
    db_session: AsyncSession,
    test_organization: Organization,
    test_team: Team,
    test_roles: dict
) -> User:
    """创建管理员用户"""
    user = User(
        username="admin",
        email="admin@test.com",
        password_hash=hash_password("password123"),
        full_name="管理员",
        role_id=test_roles["admin"].id,
        team_id=test_team.id,
        organization_id=test_organization.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_sales_user(
    db_session: AsyncSession,
    test_organization: Organization,
    test_team: Team,
    test_roles: dict
) -> User:
    """创建销售用户"""
    user = User(
        username="sales",
        email="sales@test.com",
        password_hash=hash_password("password123"),
        full_name="销售人员",
        role_id=test_roles["sales"].id,
        team_id=test_team.id,
        organization_id=test_organization.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_viewer_user(
    db_session: AsyncSession,
    test_organization: Organization,
    test_team: Team,
    test_roles: dict
) -> User:
    """创建只读用户"""
    user = User(
        username="viewer",
        email="viewer@test.com",
        password_hash=hash_password("password123"),
        full_name="只读用户",
        role_id=test_roles["viewer"].id,
        team_id=test_team.id,
        organization_id=test_organization.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_customer(
    db_session: AsyncSession,
    test_organization: Organization,
    test_sales_user: User
) -> Customer:
    """创建测试客户"""
    customer = Customer(
        name="测试客户A",
        contact="张三",
        phone="13800138001",
        email="zhangsan@test.com",
        company="测试科技公司",
        industry="互联网",
        source="线上推广",
        organization_id=test_organization.id,
        created_by=test_sales_user.id
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture(scope="function")
async def test_opportunity(
    db_session: AsyncSession,
    test_customer: Customer,
    test_sales_user: User,
    test_organization: Organization
) -> Opportunity:
    """创建测试销售机会"""
    opportunity = Opportunity(
        customer_id=test_customer.id,
        customer_name=test_customer.name,
        name="软件定制开发项目",
        amount=50000.00,
        stage="initial",
        probability=30,
        expected_date=datetime.now().date(),
        organization_id=test_organization.id,
        created_by=test_sales_user.id
    )
    db_session.add(opportunity)
    await db_session.commit()
    await db_session.refresh(opportunity)
    return opportunity


@pytest_asyncio.fixture(scope="function")
async def test_quote(
    db_session: AsyncSession,
    test_customer: Customer,
    test_opportunity: Opportunity,
    test_sales_user: User,
    test_organization: Organization
) -> Quote:
    """创建测试报价单"""
    quote = Quote(
        customer_id=test_customer.id,
        customer_name=test_customer.name,
        opportunity_id=test_opportunity.id,
        items=[
            {"name": "需求分析", "description": "需求调研", "quantity": 1, "unit_price": 5000},
            {"name": "系统开发", "description": "核心开发", "quantity": 1, "unit_price": 30000}
        ],
        total_amount=35000,
        status="draft",
        valid_until=datetime.now().date(),
        organization_id=test_organization.id,
        created_by=test_sales_user.id
    )
    db_session.add(quote)
    await db_session.commit()
    await db_session.refresh(quote)
    return quote


@pytest_asyncio.fixture(scope="function")
async def test_followup(
    db_session: AsyncSession,
    test_customer: Customer,
    test_sales_user: User,
    test_organization: Organization
) -> FollowUp:
    """创建测试跟进记录"""
    followup = FollowUp(
        customer_id=test_customer.id,
        customer_name=test_customer.name,
        content="初次沟通，客户对产品感兴趣",
        next_action="发送产品介绍资料",
        next_date=datetime.now(),
        organization_id=test_organization.id,
        created_by=test_sales_user.id
    )
    db_session.add(followup)
    await db_session.commit()
    await db_session.refresh(followup)
    return followup


# ========== 认证工具 ==========

@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_sales_user: User) -> dict:
    """生成认证请求头"""
    token = create_access_token({"sub": str(test_sales_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def admin_auth_headers(test_admin_user: User) -> dict:
    """生成管理员认证请求头"""
    token = create_access_token({"sub": str(test_admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def superuser_auth_headers(test_superuser: User) -> dict:
    """生成超级管理员认证请求头"""
    token = create_access_token({"sub": str(test_superuser.id)})
    return {"Authorization": f"Bearer {token}"}


# ========== 测试工具函数 ==========

def assert_response_success(response, expected_status=200):
    """断言响应成功"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"


def assert_response_error(response, expected_status=400):
    """断言响应错误"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"


def assert_unauthorized(response):
    """断言未授权"""
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"


def assert_forbidden(response):
    """断言权限不足"""
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"


def assert_not_found(response):
    """断言资源不存在"""
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
