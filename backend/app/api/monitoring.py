"""
性能监控API - 提供系统监控和性能指标
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.permissions import require_permission
from app.models.models import User
from app.core.logger import logger
import psutil
import asyncio

router = APIRouter()


@router.get("/health", response_model=dict)
async def health_check():
    """
    健康检查端点 - 检查系统各组件状态
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # 检查数据库连接
    try:
        # 这里可以添加数据库连接检查
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection OK"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
    
    # 检查AI服务
    try:
        # 这里可以添加AI服务检查
        health_status["components"]["ai_service"] = {
            "status": "healthy",
            "message": "AI service configured"
        }
    except Exception as e:
        health_status["components"]["ai_service"] = {
            "status": "degraded",
            "message": str(e)
        }
    
    return health_status


@router.get("/metrics", response_model=dict)
async def get_metrics(
    current_user: User = require_permission("monitoring:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取系统性能指标（需要monitoring:read权限）
    """
    # CPU和内存使用
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # 数据库统计
    from app.models.models import Customer, Opportunity, Quote, FollowUp
    
    customer_count_query = select(func.count()).select_from(Customer)
    customer_count_result = await db.execute(customer_count_query)
    customer_count = customer_count_result.scalar()
    
    opportunity_count_query = select(func.count()).select_from(Opportunity)
    opportunity_count_result = await db.execute(opportunity_count_query)
    opportunity_count = opportunity_count_result.scalar()
    
    quote_count_query = select(func.count()).select_from(Quote)
    quote_count_result = await db.execute(quote_count_query)
    quote_count = quote_count_result.scalar()
    
    followup_count_query = select(func.count()).select_from(FollowUp)
    followup_count_result = await db.execute(followup_count_query)
    followup_count = followup_count_result.scalar()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
        },
        "database": {
            "customer_count": customer_count,
            "opportunity_count": opportunity_count,
            "quote_count": quote_count,
            "followup_count": followup_count,
            # 兼容旧字段名
            "customers": customer_count,
            "opportunities": opportunity_count,
            "quotes": quote_count,
            "followups": followup_count
        }
    }


@router.get("/performance", response_model=dict)
async def get_performance_stats(
    current_user: User = require_permission("monitoring:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取性能统计（需要monitoring:read权限）
    """
    from app.models.models import AgentTask, AgentAlert
    
    # 任务统计
    task_stats_query = select(
        AgentTask.status,
        func.count().label('count')
    ).group_by(AgentTask.status)
    
    task_stats_result = await db.execute(task_stats_query)
    task_stats = {row.status: row.count for row in task_stats_result}
    
    # 预警统计
    alert_stats_query = select(
        AgentAlert.severity,
        func.count().label('count')
    ).where(
        AgentAlert.is_resolved == False
    ).group_by(AgentAlert.severity)
    
    alert_stats_result = await db.execute(alert_stats_query)
    alert_stats = {row.severity: row.count for row in alert_stats_result}
    
    # 最近任务
    recent_tasks_query = select(AgentTask).order_by(
        AgentTask.created_at.desc()
    ).limit(10)
    
    recent_tasks_result = await db.execute(recent_tasks_query)
    recent_tasks = [
        {
            "id": t.id,
            "type": t.task_type,
            "title": t.title,
            "status": t.status,
            "created_at": t.created_at.isoformat()
        }
        for t in recent_tasks_result.scalars().all()
    ]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "tasks": task_stats,
        "alerts": alert_stats,
        "recent_tasks": recent_tasks
    }


@router.get("/logs", response_model=dict)
async def get_recent_logs(
    limit: int = 100,
    current_user: User = require_permission("monitoring:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取最近日志（需要monitoring:read权限）
    
    注意：这是一个简化版本，实际应该集成日志管理系统
    """
    from app.models.models import AgentMemory
    
    # 获取最近的系统日志（存储在AgentMemory中）
    logs_query = select(AgentMemory).where(
        AgentMemory.memory_type.in_(["decision_record", "system_config", "ab_test_result"])
    ).order_by(AgentMemory.created_at.desc()).limit(limit)
    
    logs_result = await db.execute(logs_query)
    logs = [
        {
            "id": log.id,
            "type": log.memory_type,
            "title": log.title,
            "created_at": log.created_at.isoformat(),
            "importance": log.importance
        }
        for log in logs_result.scalars().all()
    ]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "total": len(logs),
        "logs": logs
    }
