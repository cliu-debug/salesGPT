"""add performance indexes

Revision ID: 002_add_indexes
Revises: 001_initial
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_indexes'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加性能优化索引"""
    
    # ========== 客户表索引 ==========
    # 组合索引：按组织+行业查询
    op.create_index(
        'ix_customers_org_industry',
        'customers',
        ['organization_id', 'industry'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+来源查询
    op.create_index(
        'ix_customers_org_source',
        'customers',
        ['organization_id', 'source'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+创建者查询（数据隔离）
    op.create_index(
        'ix_customers_org_creator',
        'customers',
        ['organization_id', 'created_by'],
        if_not_exists=True
    )
    
    # 组合索引：按创建时间排序
    op.create_index(
        'ix_customers_org_created',
        'customers',
        ['organization_id', 'created_at'],
        if_not_exists=True
    )
    
    # ========== 销售机会表索引 ==========
    # 组合索引：按组织+阶段查询
    op.create_index(
        'ix_opportunities_org_stage',
        'opportunities',
        ['organization_id', 'stage'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+预计日期查询
    op.create_index(
        'ix_opportunities_org_expected',
        'opportunities',
        ['organization_id', 'expected_date'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+创建者查询
    op.create_index(
        'ix_opportunities_org_creator',
        'opportunities',
        ['organization_id', 'created_by'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+客户查询
    op.create_index(
        'ix_opportunities_org_customer',
        'opportunities',
        ['organization_id', 'customer_id'],
        if_not_exists=True
    )
    
    # 组合索引：金额排序
    op.create_index(
        'ix_opportunities_org_amount',
        'opportunities',
        ['organization_id', 'amount'],
        if_not_exists=True
    )
    
    # ========== 报价表索引 ==========
    # 组合索引：按组织+状态查询
    op.create_index(
        'ix_quotes_org_status',
        'quotes',
        ['organization_id', 'status'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+客户查询
    op.create_index(
        'ix_quotes_org_customer',
        'quotes',
        ['organization_id', 'customer_id'],
        if_not_exists=True
    )
    
    # 组合索引：有效期查询
    op.create_index(
        'ix_quotes_org_valid',
        'quotes',
        ['organization_id', 'valid_until'],
        if_not_exists=True
    )
    
    # ========== 跟进记录表索引 ==========
    # 组合索引：按组织+客户查询
    op.create_index(
        'ix_follow_ups_org_customer',
        'follow_ups',
        ['organization_id', 'customer_id'],
        if_not_exists=True
    )
    
    # 组合索引：按下次跟进时间查询
    op.create_index(
        'ix_follow_ups_org_next_date',
        'follow_ups',
        ['organization_id', 'next_date'],
        if_not_exists=True
    )
    
    # 组合索引：按创建时间排序
    op.create_index(
        'ix_follow_ups_org_created',
        'follow_ups',
        ['organization_id', 'created_at'],
        if_not_exists=True
    )
    
    # ========== 用户表索引 ==========
    # 组合索引：按组织+角色查询
    op.create_index(
        'ix_users_org_role',
        'users',
        ['organization_id', 'role_id'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+团队查询
    op.create_index(
        'ix_users_org_team',
        'users',
        ['organization_id', 'team_id'],
        if_not_exists=True
    )
    
    # 组合索引：活跃用户查询
    op.create_index(
        'ix_users_org_active',
        'users',
        ['organization_id', 'is_active'],
        if_not_exists=True
    )
    
    # ========== 审计日志索引 ==========
    # 组合索引：按组织+时间查询
    op.create_index(
        'ix_audit_logs_org_time',
        'audit_logs',
        ['organization_id', 'created_at'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+用户查询
    op.create_index(
        'ix_audit_logs_org_user',
        'audit_logs',
        ['organization_id', 'user_id'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+操作类型查询
    op.create_index(
        'ix_audit_logs_org_action',
        'audit_logs',
        ['organization_id', 'action'],
        if_not_exists=True
    )
    
    # ========== Agent任务表索引 ==========
    # 组合索引：按组织+状态查询
    op.create_index(
        'ix_agent_tasks_org_status',
        'agent_tasks',
        ['organization_id', 'status'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+优先级查询
    op.create_index(
        'ix_agent_tasks_org_priority',
        'agent_tasks',
        ['organization_id', 'priority'],
        if_not_exists=True
    )
    
    # 组合索引：按计划执行时间查询
    op.create_index(
        'ix_agent_tasks_org_scheduled',
        'agent_tasks',
        ['organization_id', 'scheduled_at'],
        if_not_exists=True
    )
    
    # ========== Agent预警表索引 ==========
    # 组合索引：按组织+类型查询
    op.create_index(
        'ix_agent_alerts_org_type',
        'agent_alerts',
        ['organization_id', 'alert_type'],
        if_not_exists=True
    )
    
    # 组合索引：按组织+未读查询
    op.create_index(
        'ix_agent_alerts_org_unread',
        'agent_alerts',
        ['organization_id', 'is_read'],
        if_not_exists=True
    )
    
    # ========== 仪表盘统计表索引 ==========
    # 唯一约束：每个组织每天只有一条记录
    op.create_index(
        'ix_dashboard_stats_org_date',
        'dashboard_stats',
        ['organization_id', 'date'],
        unique=True,
        if_not_exists=True
    )


def downgrade() -> None:
    """移除索引"""
    
    # 客户表
    op.drop_index('ix_customers_org_industry', 'customers')
    op.drop_index('ix_customers_org_source', 'customers')
    op.drop_index('ix_customers_org_creator', 'customers')
    op.drop_index('ix_customers_org_created', 'customers')
    
    # 销售机会表
    op.drop_index('ix_opportunities_org_stage', 'opportunities')
    op.drop_index('ix_opportunities_org_expected', 'opportunities')
    op.drop_index('ix_opportunities_org_creator', 'opportunities')
    op.drop_index('ix_opportunities_org_customer', 'opportunities')
    op.drop_index('ix_opportunities_org_amount', 'opportunities')
    
    # 报价表
    op.drop_index('ix_quotes_org_status', 'quotes')
    op.drop_index('ix_quotes_org_customer', 'quotes')
    op.drop_index('ix_quotes_org_valid', 'quotes')
    
    # 跟进记录表
    op.drop_index('ix_follow_ups_org_customer', 'follow_ups')
    op.drop_index('ix_follow_ups_org_next_date', 'follow_ups')
    op.drop_index('ix_follow_ups_org_created', 'follow_ups')
    
    # 用户表
    op.drop_index('ix_users_org_role', 'users')
    op.drop_index('ix_users_org_team', 'users')
    op.drop_index('ix_users_org_active', 'users')
    
    # 审计日志表
    op.drop_index('ix_audit_logs_org_time', 'audit_logs')
    op.drop_index('ix_audit_logs_org_user', 'audit_logs')
    op.drop_index('ix_audit_logs_org_action', 'audit_logs')
    
    # Agent任务表
    op.drop_index('ix_agent_tasks_org_status', 'agent_tasks')
    op.drop_index('ix_agent_tasks_org_priority', 'agent_tasks')
    op.drop_index('ix_agent_tasks_org_scheduled', 'agent_tasks')
    
    # Agent预警表
    op.drop_index('ix_agent_alerts_org_type', 'agent_alerts')
    op.drop_index('ix_agent_alerts_org_unread', 'agent_alerts')
    
    # 仪表盘统计表
    op.drop_index('ix_dashboard_stats_org_date', 'dashboard_stats')
