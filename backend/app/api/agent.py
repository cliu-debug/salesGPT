"""
Agent智能体API接口
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.logger import logger
from app.core.auth import get_current_user
from app.core.permissions import require_permission, filter_by_organization, check_data_access
from app.services.monitoring_agent import MonitoringAgent
from app.services.memory_service import MemoryService
from app.models.models import AgentAlert, AgentTask, AgentGoal, AgentMemory, User

router = APIRouter()


@router.get("/alerts", response_model=dict)
async def get_alerts(
    severity: Optional[str] = None,
    is_resolved: bool = False,
    limit: int = 20,
    current_user: User = require_permission("agent:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取预警列表（需要agent:read权限，自动数据隔离）
    """
    agent = MonitoringAgent(db)
    alerts = await agent.get_active_alerts(severity=severity, limit=limit, user=current_user)
    
    return {
        "total": len(alerts),
        "items": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "entity_name": a.entity_name,
                "suggested_action": a.suggested_action,
                "is_read": a.is_read,
                "is_resolved": a.is_resolved,
                "created_at": a.created_at
            }
            for a in alerts
        ]
    }


@router.get("/alerts/summary", response_model=dict)
async def get_alert_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    获取预警摘要
    """
    agent = MonitoringAgent(db)
    summary = await agent.get_alert_summary()
    return summary


@router.post("/alerts/{alert_id}/resolve", response_model=dict)
async def resolve_alert(
    alert_id: int,
    action_taken: Optional[str] = None,
    current_user: User = require_permission("agent:write"),
    db: AsyncSession = Depends(get_db)
):
    """
    解决预警（需要agent:write权限和数据访问权限）
    """
    # 检查数据访问权限
    await check_data_access(db, current_user, AgentAlert, alert_id)
    
    agent = MonitoringAgent(db)
    alert = await agent.resolve_alert(alert_id, action_taken)
    
    if not alert:
        return {"error": "预警不存在"}
    
    return {
        "id": alert.id,
        "is_resolved": alert.is_resolved,
        "resolved_at": alert.resolved_at,
        "message": "预警已解决"
    }


@router.post("/alerts/{alert_id}/read", response_model=dict)
async def mark_alert_read(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    标记预警为已读
    """
    from sqlalchemy import select
    
    query = select(AgentAlert).where(AgentAlert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    
    if not alert:
        return {"error": "预警不存在"}
    
    alert.is_read = True
    await db.commit()
    
    return {"message": "已标记为已读"}


@router.post("/scan", response_model=dict)
async def trigger_scan(
    current_user: User = require_permission("agent:execute"),
    db: AsyncSession = Depends(get_db)
):
    """
    手动触发监控扫描（需要agent:execute权限）
    """
    agent = MonitoringAgent(db)
    alerts = await agent.scan_all(user=current_user)
    
    return {
        "scanned_at": datetime.now(),
        "new_alerts": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "type": a.alert_type,
                "severity": a.severity,
                "title": a.title
            }
            for a in alerts
        ]
    }


@router.get("/briefing", response_model=dict)
async def get_daily_briefing(
    db: AsyncSession = Depends(get_db)
):
    """
    获取每日简报
    """
    agent = MonitoringAgent(db)
    briefing = await agent.generate_daily_briefing()
    return briefing


@router.get("/dashboard", response_model=dict)
async def get_agent_dashboard(
    current_user: User = require_permission("agent:read"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取智能体工作台数据（需要agent:read权限，自动数据隔离）
    """
    from sqlalchemy import select, func, and_
    from app.models.models import Customer, Opportunity, FollowUp, Quote
    from datetime import timedelta
    
    agent = MonitoringAgent(db)
    
    summary = await agent.get_alert_summary(user=current_user)
    alerts = await agent.get_active_alerts(limit=5, user=current_user)
    briefing = await agent.generate_daily_briefing(user=current_user)
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59)
    
    today_followups_query = select(FollowUp).where(
        and_(
            FollowUp.next_date >= today_start,
            FollowUp.next_date <= today_end
        )
    )
    # 数据隔离过滤
    today_followups_query = filter_by_organization(today_followups_query, FollowUp, current_user)
    today_followups_query = today_followups_query.order_by(FollowUp.next_date).limit(5)
    
    result = await db.execute(today_followups_query)
    today_followups = result.scalars().all()
    
    active_goals_query = select(AgentGoal).where(
        AgentGoal.status == "active"
    )
    # 数据隔离过滤
    active_goals_query = filter_by_organization(active_goals_query, AgentGoal, current_user)
    active_goals_query = active_goals_query.order_by(AgentGoal.created_at.desc()).limit(3)
    
    result = await db.execute(active_goals_query)
    active_goals = result.scalars().all()
    
    pending_tasks_query = select(AgentTask).where(
        AgentTask.status == "pending"
    )
    # 数据隔离过滤
    pending_tasks_query = filter_by_organization(pending_tasks_query, AgentTask, current_user)
    pending_tasks_query = pending_tasks_query.order_by(AgentTask.priority.desc(), AgentTask.scheduled_at).limit(5)
    
    result = await db.execute(pending_tasks_query)
    pending_tasks = result.scalars().all()
    
    return {
        "alert_summary": summary,
        "recent_alerts": [
            {
                "id": a.id,
                "type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "entity_name": a.entity_name,
                "suggested_action": a.suggested_action,
                "created_at": a.created_at
            }
            for a in alerts
        ],
        "today_followups": [
            {
                "id": f.id,
                "customer_name": f.customer_name,
                "next_action": f.next_action,
                "next_date": f.next_date
            }
            for f in today_followups
        ],
        "active_goals": [
            {
                "id": g.id,
                "name": g.name,
                "target_value": g.target_value,
                "current_value": g.current_value,
                "unit": g.unit,
                "progress": (g.current_value / g.target_value * 100) if g.target_value > 0 else 0,
                "end_date": g.end_date
            }
            for g in active_goals
        ],
        "pending_tasks": [
            {
                "id": t.id,
                "task_type": t.task_type,
                "title": t.title,
                "priority": t.priority,
                "scheduled_at": t.scheduled_at
            }
            for t in pending_tasks
        ],
        "briefing": briefing
    }


@router.get("/memories", response_model=dict)
async def get_memories(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    memory_type: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    获取记忆列表
    """
    memory_service = MemoryService(db)
    memories = await memory_service.recall(
        entity_type=entity_type,
        entity_id=entity_id,
        memory_type=memory_type,
        limit=limit
    )
    
    return {
        "total": len(memories),
        "items": [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "entity_type": m.entity_type,
                "entity_id": m.entity_id,
                "title": m.title,
                "content": m.content,
                "importance": m.importance,
                "access_count": m.access_count,
                "created_at": m.created_at
            }
            for m in memories
        ]
    }


@router.post("/memories", response_model=dict)
async def create_memory(
    memory_type: str,
    content: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    title: Optional[str] = None,
    importance: float = 0.5,
    db: AsyncSession = Depends(get_db)
):
    """
    创建记忆
    """
    memory_service = MemoryService(db)
    memory = await memory_service.store(
        content=content,
        memory_type=memory_type,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        importance=importance
    )
    
    return {
        "id": memory.id,
        "message": "记忆创建成功"
    }


@router.get("/memories/customer/{customer_id}", response_model=dict)
async def get_customer_memories(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取客户相关记忆
    """
    memory_service = MemoryService(db)
    context = await memory_service.recall_customer_context(customer_id)
    return context


@router.get("/goals", response_model=dict)
async def get_goals(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取目标列表
    """
    from sqlalchemy import select
    
    query = select(AgentGoal)
    if status:
        query = query.where(AgentGoal.status == status)
    
    query = query.order_by(AgentGoal.created_at.desc())
    result = await db.execute(query)
    goals = result.scalars().all()
    
    return {
        "total": len(goals),
        "items": [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "goal_type": g.goal_type,
                "target_value": g.target_value,
                "current_value": g.current_value,
                "unit": g.unit,
                "progress": (g.current_value / g.target_value * 100) if g.target_value > 0 else 0,
                "start_date": g.start_date,
                "end_date": g.end_date,
                "status": g.status
            }
            for g in goals
        ]
    }


@router.post("/goals", response_model=dict)
async def create_goal(
    name: str,
    target_value: float,
    unit: str = "元",
    goal_type: str = "revenue",
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = require_permission("agent:write"),
    db: AsyncSession = Depends(get_db)
):
    """
    创建目标（需要agent:write权限）
    """
    goal = AgentGoal(
        name=name,
        description=description,
        goal_type=goal_type,
        target_value=target_value,
        unit=unit,
        start_date=datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None,
        end_date=datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None,
        # 数据隔离字段
        organization_id=current_user.organization_id,
        user_id=current_user.id
    )
    
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    
    return {
        "id": goal.id,
        "message": "目标创建成功"
    }


@router.put("/goals/{goal_id}/progress", response_model=dict)
async def update_goal_progress(
    goal_id: int,
    current_value: float,
    db: AsyncSession = Depends(get_db)
):
    """
    更新目标进度
    """
    from sqlalchemy import select
    
    query = select(AgentGoal).where(AgentGoal.id == goal_id)
    result = await db.execute(query)
    goal = result.scalar_one_or_none()
    
    if not goal:
        return {"error": "目标不存在"}
    
    goal.current_value = current_value
    
    if current_value >= goal.target_value:
        goal.status = "completed"
    
    await db.commit()
    
    return {
        "id": goal.id,
        "current_value": goal.current_value,
        "progress": (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0,
        "status": goal.status
    }


@router.get("/tasks", response_model=dict)
async def get_tasks(
    status: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务列表
    """
    from sqlalchemy import select
    
    query = select(AgentTask)
    if status:
        query = query.where(AgentTask.status == status)
    
    query = query.order_by(AgentTask.priority.desc(), AgentTask.created_at.desc()).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "total": len(tasks),
        "items": [
            {
                "id": t.id,
                "task_type": t.task_type,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "target_entity_type": t.target_entity_type,
                "target_entity_id": t.target_entity_id,
                "scheduled_at": t.scheduled_at,
                "completed_at": t.completed_at,
                "created_at": t.created_at
            }
            for t in tasks
        ]
    }


@router.post("/tasks/{task_id}/complete", response_model=dict)
async def complete_task(
    task_id: int,
    result_data: Optional[dict] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    完成任务
    """
    from sqlalchemy import select
    
    query = select(AgentTask).where(AgentTask.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    
    if not task:
        return {"error": "任务不存在"}
    
    task.status = "completed"
    task.completed_at = datetime.now()
    if result_data:
        task.result = result_data
    
    await db.commit()
    
    return {
        "id": task.id,
        "status": task.status,
        "message": "任务已完成"
    }


@router.post("/workflow/daily", response_model=dict)
async def run_daily_workflow(
    db: AsyncSession = Depends(get_db)
):
    """
    执行每日工作流
    """
    from app.services.agent_supervisor import AgentSupervisor
    
    supervisor = AgentSupervisor(db)
    result = await supervisor.run_daily_workflow()
    
    return result


@router.get("/analysis/funnel", response_model=dict)
async def analyze_funnel(
    db: AsyncSession = Depends(get_db)
):
    """
    分析销售漏斗
    """
    from app.services.analysis_agent import AnalysisAgent
    
    agent = AnalysisAgent(db)
    result = await agent.analyze_sales_funnel()
    
    return result


@router.get("/analysis/trend", response_model=dict)
async def analyze_trend(
    months: int = 6,
    db: AsyncSession = Depends(get_db)
):
    """
    分析销售趋势
    """
    from app.services.analysis_agent import AnalysisAgent
    
    agent = AnalysisAgent(db)
    result = await agent.analyze_sales_trend(months)
    
    return result


@router.get("/analysis/lost-deals", response_model=dict)
async def analyze_lost_deals(
    days: int = 90,
    db: AsyncSession = Depends(get_db)
):
    """
    分析丢单原因
    """
    from app.services.analysis_agent import AnalysisAgent
    
    agent = AnalysisAgent(db)
    result = await agent.analyze_lost_deals(days)
    
    return result


@router.get("/analysis/customer/{customer_id}/value", response_model=dict)
async def analyze_customer_value(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    分析客户价值
    """
    from app.services.analysis_agent import AnalysisAgent
    
    agent = AnalysisAgent(db)
    result = await agent.analyze_customer_value(customer_id)
    
    return result


@router.get("/analysis/opportunity/{opportunity_id}/risk", response_model=dict)
async def analyze_opportunity_risk(
    opportunity_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    分析机会风险
    """
    from app.services.analysis_agent import AnalysisAgent
    
    agent = AnalysisAgent(db)
    result = await agent.analyze_opportunity_risk(opportunity_id)
    
    return result


@router.get("/analysis/insights", response_model=dict)
async def generate_sales_insights(
    db: AsyncSession = Depends(get_db)
):
    """
    生成销售洞察
    """
    from app.services.analysis_agent import AnalysisAgent
    
    agent = AnalysisAgent(db)
    result = await agent.generate_sales_insights()
    
    return result


@router.get("/report/daily", response_model=dict)
async def get_daily_report(
    db: AsyncSession = Depends(get_db)
):
    """
    获取日报
    """
    from app.services.notification_agent import NotificationAgent
    
    agent = NotificationAgent(db)
    result = await agent.generate_daily_report()
    
    return result


@router.get("/report/weekly", response_model=dict)
async def get_weekly_report(
    db: AsyncSession = Depends(get_db)
):
    """
    获取周报
    """
    from app.services.notification_agent import NotificationAgent
    
    agent = NotificationAgent(db)
    result = await agent.generate_weekly_report()
    
    return result


@router.get("/report/weekly-summary", response_model=dict)
async def get_weekly_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    获取周度总结
    """
    from app.services.agent_supervisor import AgentSupervisor
    
    supervisor = AgentSupervisor(db)
    result = await supervisor.generate_weekly_summary()
    
    return result


@router.get("/goals/progress", response_model=dict)
async def check_goals_progress(
    db: AsyncSession = Depends(get_db)
):
    """
    检查目标进度
    """
    from app.services.notification_agent import NotificationAgent
    
    agent = NotificationAgent(db)
    result = await agent.check_goal_progress()
    
    return {
        "goals": result
    }


@router.get("/status", response_model=dict)
async def get_agent_status(
    db: AsyncSession = Depends(get_db)
):
    """
    获取Agent状态
    """
    from app.services.agent_supervisor import AgentSupervisor
    
    supervisor = AgentSupervisor(db)
    result = await supervisor.get_agent_status()
    
    return result


@router.post("/dispatch", response_model=dict)
async def smart_dispatch(
    request: str,
    db: AsyncSession = Depends(get_db)
):
    """
    智能分发请求
    """
    from app.services.agent_supervisor import AgentSupervisor
    
    supervisor = AgentSupervisor(db)
    result = await supervisor.smart_dispatch(request)
    
    return result


@router.post("/tasks/create", response_model=dict)
async def create_agent_task(
    task_type: str,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    target_entity_type: Optional[str] = None,
    target_entity_id: Optional[int] = None,
    action_plan: Optional[dict] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    创建Agent任务
    """
    from app.services.execution_agent import ExecutionAgent
    
    agent = ExecutionAgent(db)
    task = await agent.create_task(
        task_type=task_type,
        title=title,
        description=description,
        priority=priority,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        action_plan=action_plan
    )
    
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "message": "任务创建成功"
    }


@router.post("/tasks/{task_id}/execute", response_model=dict)
async def execute_agent_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    执行Agent任务
    """
    from app.services.execution_agent import ExecutionAgent
    
    agent = ExecutionAgent(db)
    result = await agent.execute_task(task_id)
    
    return result


@router.post("/followups/schedule", response_model=dict)
async def schedule_followup(
    customer_id: int,
    content: str,
    next_action: Optional[str] = None,
    next_date: Optional[str] = None,
    priority: str = "medium",
    db: AsyncSession = Depends(get_db)
):
    """
    安排跟进任务
    """
    from app.services.execution_agent import ExecutionAgent
    
    agent = ExecutionAgent(db)
    
    next_datetime = None
    if next_date:
        next_datetime = datetime.fromisoformat(next_date)
    
    task = await agent.schedule_followup(
        customer_id=customer_id,
        content=content,
        next_action=next_action,
        next_date=next_datetime,
        priority=priority
    )
    
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "message": "跟进任务已安排"
    }


@router.post("/autonomous/cycle", response_model=dict)
async def run_autonomous_cycle(
    auto_execute: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    执行自主决策周期
    """
    from app.services.autonomous_agent import AutonomousAgent
    
    agent = AutonomousAgent(db)
    result = await agent.run_autonomous_cycle(auto_execute=auto_execute)
    
    return result


@router.get("/autonomous/perception", response_model=dict)
async def get_perception(
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前感知状态
    """
    from app.services.autonomous_agent import AutonomousAgent
    
    agent = AutonomousAgent(db)
    result = await agent.perceive()
    
    return result


@router.get("/autonomous/decisions", response_model=dict)
async def get_pending_decisions(
    db: AsyncSession = Depends(get_db)
):
    """
    获取待确认的决策
    """
    from app.services.autonomous_agent import AutonomousAgent
    
    agent = AutonomousAgent(db)
    result = await agent.get_pending_decisions()
    
    return {
        "pending_count": len(result),
        "decisions": result
    }


@router.post("/autonomous/execute", response_model=dict)
async def execute_decision(
    decision: dict,
    auto_confirm: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    执行决策
    """
    from app.services.autonomous_agent import AutonomousAgent
    
    agent = AutonomousAgent(db)
    result = await agent.execute(decision, auto_confirm=auto_confirm)
    
    return result


@router.post("/autonomous/confirm", response_model=dict)
async def confirm_and_execute(
    decision: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    确认并执行决策
    """
    from app.services.autonomous_agent import AutonomousAgent
    
    agent = AutonomousAgent(db)
    result = await agent.confirm_and_execute(decision)
    
    return result


@router.post("/autonomous/reject", response_model=dict)
async def reject_decision(
    decision: dict,
    reason: str = "",
    db: AsyncSession = Depends(get_db)
):
    """
    拒绝决策
    """
    from app.services.autonomous_agent import AutonomousAgent
    
    agent = AutonomousAgent(db)
    result = await agent.reject_decision(decision, reason)
    
    return result


@router.post("/autonomous/feedback", response_model=dict)
async def provide_feedback(
    decision_id: str,
    outcome: str,
    comment: str = "",
    db: AsyncSession = Depends(get_db)
):
    """
    提供决策反馈用于学习
    """
    from app.services.autonomous_agent import AutonomousAgent
    
    agent = AutonomousAgent(db)
    result = await agent.learn_from_feedback(
        decision_id,
        {"outcome": outcome, "comment": comment}
    )
    
    return result


@router.post("/chat", response_model=dict)
async def chat_with_agent(
    message: str,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    与智能体对话
    """
    from app.services.agent_supervisor import AgentSupervisor
    from app.services.memory_service import MemoryService
    import uuid
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    supervisor = AgentSupervisor(db)
    memory_service = MemoryService(db)
    
    dispatch_result = await supervisor.smart_dispatch(message)
    
    response = {
        "session_id": session_id,
        "message": message,
        "understood_intent": dispatch_result.get("dispatched_to", []),
        "results": dispatch_result.get("results", []),
        "suggestions": []
    }
    
    if dispatch_result.get("results"):
        for result in dispatch_result["results"]:
            if "insights" in result:
                insights = result["insights"]
                if insights.get("ai_insights"):
                    response["suggestions"].extend(
                        insights["ai_insights"].get("recommendations", [])
                    )
            if "reminders" in result:
                reminders = result["reminders"]
                if reminders.get("summary"):
                    response["suggestions"].append(
                        f"今日有 {reminders['summary']['total_followups']} 个跟进任务待完成"
                    )
    
    if not response["suggestions"]:
        response["suggestions"] = [
            "您可以问我关于销售数据的问题",
            "我可以帮您分析客户或机会",
            "我可以提醒您今日待办事项"
        ]
    
    await memory_service.store_session_context(
        session_id=session_id,
        context={
            "last_message": message,
            "last_response": response
        }
    )
    
    return response


@router.get("/recommendations", response_model=dict)
async def get_recommendations(
    db: AsyncSession = Depends(get_db)
):
    """
    获取智能推荐
    """
    from app.services.autonomous_agent import AutonomousAgent
    from app.services.analysis_agent import AnalysisAgent
    
    autonomous_agent = AutonomousAgent(db)
    analysis_agent = AnalysisAgent(db)
    
    perception = await autonomous_agent.perceive()
    decisions = await autonomous_agent.decide(perception)
    
    insights = await analysis_agent.generate_sales_insights()
    
    recommendations = []
    
    for decision in decisions[:3]:
        recommendations.append({
            "type": decision["decision_type"],
            "priority": decision["priority"],
            "action": decision["action"],
            "target": decision["target"],
            "reason": decision["reason"],
            "auto_executable": decision.get("auto_executable", False)
        })
    
    if insights.get("ai_insights"):
        for rec in insights["ai_insights"].get("recommendations", [])[:3]:
            recommendations.append({
                "type": "insight",
                "priority": "medium",
                "action": rec,
                "target": None,
                "reason": "AI分析建议",
                "auto_executable": False
            })
    
    return {
        "total": len(recommendations),
        "recommendations": recommendations
    }
