from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from app.models.models import CustomerStatus, OpportunityStage, QuoteStatus


class CustomerCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = "potential"
    tags: Optional[List[str]] = None
    remark: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    remark: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    contact: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    company: Optional[str]
    industry: Optional[str]
    source: Optional[str]
    status: str
    tags: Optional[List[str]]
    ai_profile: Optional[Dict[str, Any]]
    remark: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OpportunityCreate(BaseModel):
    customer_id: int
    customer_name: Optional[str] = None
    name: str
    amount: Optional[float] = 0
    stage: Optional[str] = "initial"
    expected_date: Optional[date] = None
    remark: Optional[str] = None


class OpportunityUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    stage: Optional[str] = None
    probability: Optional[float] = None
    expected_date: Optional[date] = None
    remark: Optional[str] = None


class OpportunityResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str]
    name: str
    amount: float
    stage: str
    probability: float
    expected_date: Optional[date]
    ai_suggestion: Optional[Dict[str, Any]]
    remark: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuoteItem(BaseModel):
    name: str
    description: Optional[str] = None
    quantity: float = 1
    unit_price: float = 0
    amount: float = 0


class QuoteCreate(BaseModel):
    customer_id: int
    customer_name: Optional[str] = None
    opportunity_id: Optional[int] = None
    items: List[QuoteItem]
    valid_until: Optional[date] = None
    remark: Optional[str] = None


class QuoteUpdate(BaseModel):
    items: Optional[List[QuoteItem]] = None
    status: Optional[str] = None
    valid_until: Optional[date] = None
    remark: Optional[str] = None


class QuoteResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str]
    opportunity_id: Optional[int]
    items: List[Dict[str, Any]]
    total_amount: float
    status: str
    ai_price_suggestion: Optional[Dict[str, Any]]
    valid_until: Optional[date]
    remark: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FollowUpCreate(BaseModel):
    customer_id: int
    customer_name: Optional[str] = None
    content: str
    next_action: Optional[str] = None
    next_date: Optional[datetime] = None


class FollowUpResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str]
    content: str
    next_action: Optional[str]
    next_date: Optional[datetime]
    ai_script: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    total_customers: int
    new_customers_this_month: int
    total_opportunities: int
    total_amount: float
    won_amount: float
    conversion_rate: float
    stage_distribution: Dict[str, int]
    recent_customers: List[Dict[str, Any]]
    recent_opportunities: List[Dict[str, Any]]


# ===== 认证相关 Schema =====
class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class Token(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: 'UserResponse'


class TokenPayload(BaseModel):
    """Token载荷"""
    sub: int  # user_id
    exp: datetime
    iat: datetime


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    avatar: Optional[str]
    is_active: bool
    is_superuser: bool
    role_id: Optional[int]
    role_name: Optional[str] = None
    team_id: Optional[int]
    team_name: Optional[str] = None
    organization_id: int
    organization_name: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户信息更新"""
    full_name: Optional[str] = Field(None, max_length=100)
    avatar: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None
    preferences: Optional[Dict[str, Any]] = None


class PasswordChange(BaseModel):
    """密码修改"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class RoleCreate(BaseModel):
    """创建角色"""
    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=50)
    permissions: List[str]
    description: Optional[str] = None


class RoleResponse(BaseModel):
    """角色信息响应"""
    id: int
    name: str
    code: str
    permissions: List[str]
    description: Optional[str]
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    """创建团队"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class TeamResponse(BaseModel):
    """团队信息响应"""
    id: int
    name: str
    description: Optional[str]
    organization_id: int
    created_at: datetime
    member_count: Optional[int] = 0

    class Config:
        from_attributes = True


class OrganizationCreate(BaseModel):
    """创建组织"""
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=100)
    plan: Optional[str] = "free"


class OrganizationResponse(BaseModel):
    """组织信息响应"""
    id: int
    name: str
    slug: str
    plan: str
    settings: Optional[Dict[str, Any]]
    is_active: bool
    max_users: int
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    """审计日志响应"""
    id: int
    user_id: Optional[int]
    username: Optional[str]
    organization_id: int
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    entity_name: Optional[str]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# 更新前向引用
Token.model_rebuild()
