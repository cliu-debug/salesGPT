from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Date, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class CustomerStatus(str, enum.Enum):
    POTENTIAL = "potential"
    INTERESTED = "interested"
    NEGOTIATING = "negotiating"
    CLOSED = "closed"
    LOST = "lost"


class OpportunityStage(str, enum.Enum):
    INITIAL = "initial"
    NEED_CONFIRM = "need_confirm"
    QUOTING = "quoting"
    NEGOTIATING = "negotiating"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class QuoteStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class MemoryType(str, enum.Enum):
    SHORT_TERM = "short_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AlertType(str, enum.Enum):
    CUSTOMER_CHURN_RISK = "customer_churn_risk"
    OPPORTUNITY_STALLED = "opportunity_stalled"
    FOLLOWUP_OVERDUE = "followup_overdue"
    QUOTE_EXPIRING = "quote_expiring"
    HIGH_VALUE_OPPORTUNITY = "high_value_opportunity"
    DEAL_PROBABILITY_DROP = "deal_probability_drop"


# ===== 用户系统枚举 =====
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"  # 超级管理员
    ADMIN = "admin"              # 管理员
    MANAGER = "manager"          # 经理
    SALES = "sales"              # 销售人员
    VIEWER = "viewer"            # 只读用户


class OrganizationPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ===== 用户系统模型 =====
class Organization(Base):
    """组织/租户"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, index=True)  # URL友好的唯一标识
    plan = Column(String(50), default=OrganizationPlan.FREE.value)
    settings = Column(JSON)  # 组织自定义设置
    is_active = Column(Boolean, default=True)
    max_users = Column(Integer, default=10)  # 最大用户数
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    teams = relationship("Team", back_populates="organization")
    users = relationship("User", back_populates="organization")


class Team(Base):
    """团队"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    organization = relationship("Organization", back_populates="teams")
    users = relationship("User", back_populates="team")


class Role(Base):
    """角色"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    code = Column(String(50), nullable=False, index=True)  # super_admin, admin, manager, sales, viewer
    permissions = Column(JSON)  # ["customer:read", "customer:write", "opportunity:read", ...]
    description = Column(Text)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)  # 可为NULL表示系统默认角色
    is_system = Column(Boolean, default=False)  # 是否系统角色
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    users = relationship("User", back_populates="role")


class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    avatar = Column(String(500))  # 头像URL
    role_id = Column(Integer, ForeignKey("roles.id"), index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # 是否超级管理员
    last_login = Column(DateTime)
    preferences = Column(JSON)  # 用户偏好设置
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    role = relationship("Role", back_populates="users")
    team = relationship("Team", back_populates="users")
    organization = relationship("Organization", back_populates="users")


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    username = Column(String(50))
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    action = Column(String(100), nullable=False)  # create_customer, update_opportunity, delete_quote
    entity_type = Column(String(50))  # customer, opportunity, quote
    entity_id = Column(Integer)
    entity_name = Column(String(200))
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    request_id = Column(String(100))  # 请求追踪ID
    created_at = Column(DateTime, server_default=func.now())


# ===== 业务模型 =====



class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    contact = Column(String(50))
    phone = Column(String(20))
    email = Column(String(100))
    company = Column(String(200))
    industry = Column(String(50))
    source = Column(String(50))
    status = Column(String(20), default=CustomerStatus.POTENTIAL.value)
    tags = Column(JSON)
    ai_profile = Column(JSON)
    remark = Column(Text)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    created_by = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    customer_name = Column(String(100))
    name = Column(String(200), nullable=False)
    amount = Column(Float, default=0)
    stage = Column(String(20), default=OpportunityStage.INITIAL.value)
    probability = Column(Float, default=0)
    expected_date = Column(Date)
    ai_suggestion = Column(JSON)
    remark = Column(Text)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    created_by = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    customer_name = Column(String(100))
    opportunity_id = Column(Integer)
    items = Column(JSON)
    total_amount = Column(Float, default=0)
    status = Column(String(20), default=QuoteStatus.DRAFT.value)
    ai_price_suggestion = Column(JSON)
    valid_until = Column(Date)
    remark = Column(Text)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    created_by = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    customer_name = Column(String(100))
    content = Column(Text, nullable=False)
    next_action = Column(String(500))
    next_date = Column(DateTime)
    ai_script = Column(Text)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    created_by = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())


class DashboardStats(Base):
    __tablename__ = "dashboard_stats"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    total_customers = Column(Integer, default=0)
    new_customers = Column(Integer, default=0)
    total_opportunities = Column(Integer, default=0)
    total_amount = Column(Float, default=0)
    won_amount = Column(Float, default=0)
    conversion_rate = Column(Float, default=0)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())


class AgentMemory(Base):
    """
    Agent记忆系统 - 存储智能体的记忆数据
    支持短期记忆、语义记忆和情节记忆
    """
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, index=True)
    memory_type = Column(String(20), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    title = Column(String(200))
    content = Column(Text, nullable=False)
    embedding = Column(Text)
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    extra_data = Column(JSON)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    last_accessed = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)


class AgentTask(Base):
    """
    Agent任务系统 - 存储智能体的任务队列
    """
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    priority = Column(String(20), default=TaskPriority.MEDIUM.value)
    status = Column(String(20), default=TaskStatus.PENDING.value)
    target_entity_type = Column(String(50))
    target_entity_id = Column(Integer)
    action_plan = Column(JSON)
    result = Column(JSON)
    error_message = Column(Text)
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AgentAlert(Base):
    """
    Agent预警系统 - 存储智能体发现的预警信息
    """
    __tablename__ = "agent_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="medium")
    title = Column(String(200), nullable=False)
    description = Column(Text)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    entity_name = Column(String(200))
    suggested_action = Column(Text)
    action_taken = Column(Text)
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(100))
    extra_data = Column(JSON)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AgentGoal(Base):
    """
    Agent目标系统 - 存储销售目标和进度
    """
    __tablename__ = "agent_goals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    goal_type = Column(String(50))
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0)
    unit = Column(String(20))
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default="active")
    milestones = Column(JSON)
    strategies = Column(JSON)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AgentConversation(Base):
    """
    Agent对话系统 - 存储与用户的对话历史
    """
    __tablename__ = "agent_conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String(100))
    entities = Column(JSON)
    action_taken = Column(String(200))
    is_processed = Column(Boolean, default=False)
    # 数据隔离字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
