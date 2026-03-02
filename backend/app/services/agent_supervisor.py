"""
Agent协调器(Supervisor) - 协调多个Agent之间的协作
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AgentTask, AgentAlert, AgentGoal, AgentMemory
from app.services.monitoring_agent import MonitoringAgent
from app.services.analysis_agent import AnalysisAgent
from app.services.execution_agent import ExecutionAgent
from app.services.notification_agent import NotificationAgent
from app.services.memory_service import MemoryService
from app.core.logger import logger


class AgentSupervisor:
    """
    Agent协调器 - 协调多个Agent之间的协作
    
    职责:
    1. 任务分配 - 根据任务类型分配给合适的Agent
    2. 工作流编排 - 协调多Agent完成复杂任务
    3. 结果汇总 - 汇总各Agent的执行结果
    4. 状态监控 - 监控各Agent的运行状态
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.monitoring_agent = MonitoringAgent(db)
        self.analysis_agent = AnalysisAgent(db)
        self.execution_agent = ExecutionAgent(db)
        self.notification_agent = NotificationAgent(db)
        self.memory_service = MemoryService(db)
    
    async def run_daily_workflow(self) -> Dict[str, Any]:
        """
        执行每日工作流
        """
        workflow_start = datetime.now()
        workflow_results = {
            "started_at": workflow_start.isoformat(),
            "steps": [],
            "summary": {}
        }
        
        logger.info("开始执行每日工作流...")
        
        step1 = await self.monitoring_agent.scan_all()
        workflow_results["steps"].append({
            "step": "monitoring_scan",
            "status": "completed",
            "alerts_found": len(step1)
        })
        
        step2 = await self.monitoring_agent.generate_daily_briefing()
        workflow_results["steps"].append({
            "step": "daily_briefing",
            "status": "completed",
            "alerts_count": step2.get("summary", {}).get("total_alerts", 0)
        })
        
        step3 = await self.analysis_agent.analyze_sales_funnel()
        workflow_results["steps"].append({
            "step": "funnel_analysis",
            "status": "completed",
            "total_opportunities": step3.get("total_opportunities", 0)
        })
        
        step4 = await self.notification_agent.get_today_reminders()
        workflow_results["steps"].append({
            "step": "today_reminders",
            "status": "completed",
            "followups_count": step4.get("summary", {}).get("total_followups", 0)
        })
        
        step5 = await self.notification_agent.check_goal_progress()
        workflow_results["steps"].append({
            "step": "goal_progress_check",
            "status": "completed",
            "goals_count": len(step5)
        })
        
        expired_count = await self.memory_service.forget_expired()
        workflow_results["steps"].append({
            "step": "memory_cleanup",
            "status": "completed",
            "expired_memories": expired_count
        })
        
        workflow_end = datetime.now()
        duration = (workflow_end - workflow_start).total_seconds()
        
        workflow_results["completed_at"] = workflow_end.isoformat()
        workflow_results["duration_seconds"] = duration
        workflow_results["summary"] = {
            "total_steps": len(workflow_results["steps"]),
            "alerts_generated": len(step1),
            "followups_today": step4.get("summary", {}).get("total_followups", 0),
            "goals_tracked": len(step5)
        }
        
        await self.memory_service.store(
            content=f"每日工作流完成，发现{len(step1)}条预警，{step4.get('summary', {}).get('total_followups', 0)}个今日待办",
            memory_type="episodic",
            entity_type="workflow",
            title="每日工作流执行记录",
            importance=0.7
        )
        
        logger.info(f"每日工作流完成，耗时 {duration:.2f} 秒")
        
        return workflow_results
    
    async def handle_alert_workflow(
        self,
        alert_id: int
    ) -> Dict[str, Any]:
        """
        处理预警的工作流
        """
        from sqlalchemy import select
        
        query = select(AgentAlert).where(AgentAlert.id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            return {"success": False, "error": "预警不存在"}
        
        workflow = {
            "alert_id": alert_id,
            "alert_type": alert.alert_type,
            "steps": []
        }
        
        if alert.entity_type == "customer":
            analysis = await self.analysis_agent.analyze_customer_value(alert.entity_id)
            workflow["steps"].append({
                "step": "customer_analysis",
                "result": analysis
            })
        
        elif alert.entity_type == "opportunity":
            analysis = await self.analysis_agent.analyze_opportunity_risk(alert.entity_id)
            workflow["steps"].append({
                "step": "opportunity_analysis",
                "result": analysis
            })
        
        if alert.alert_type == "customer_churn_risk":
            task = await self.execution_agent.schedule_followup(
                customer_id=alert.entity_id,
                content=f"客户流失预警：{alert.description}",
                next_action="主动联系客户，了解最新需求"
            )
            workflow["steps"].append({
                "step": "create_followup_task",
                "task_id": task.id
            })
        
        resolved = await self.monitoring_agent.resolve_alert(
            alert_id,
            action_taken="已创建跟进任务"
        )
        workflow["steps"].append({
            "step": "resolve_alert",
            "resolved": resolved is not None
        })
        
        workflow["success"] = True
        workflow["completed_at"] = datetime.now().isoformat()
        
        return workflow
    
    async def process_high_value_opportunity(
        self,
        opportunity_id: int
    ) -> Dict[str, Any]:
        """
        处理高价值机会的工作流
        """
        workflow = {
            "opportunity_id": opportunity_id,
            "steps": []
        }
        
        risk_analysis = await self.analysis_agent.analyze_opportunity_risk(opportunity_id)
        workflow["steps"].append({
            "step": "risk_analysis",
            "result": risk_analysis
        })
        
        from sqlalchemy import select
        from app.models.models import Opportunity
        
        query = select(Opportunity).where(Opportunity.id == opportunity_id)
        result = await self.db.execute(query)
        opp = result.scalar_one_or_none()
        
        if opp and opp.customer_id:
            customer_analysis = await self.analysis_agent.analyze_customer_value(opp.customer_id)
            workflow["steps"].append({
                "step": "customer_analysis",
                "customer_id": opp.customer_id,
                "result": customer_analysis
            })
        
        await self.memory_service.store_knowledge(
            entity_type="opportunity",
            entity_id=opportunity_id,
            knowledge_type="high_value_flag",
            content=f"高价值机会标记，风险等级: {risk_analysis.get('risk_level', '未知')}",
            importance=0.9
        )
        
        workflow["success"] = True
        workflow["completed_at"] = datetime.now().isoformat()
        
        return workflow
    
    async def generate_weekly_summary(self) -> Dict[str, Any]:
        """
        生成周度总结
        """
        summary = {
            "generated_at": datetime.now().isoformat(),
            "sections": {}
        }
        
        weekly_report = await self.notification_agent.generate_weekly_report()
        summary["sections"]["weekly_report"] = weekly_report
        
        funnel = await self.analysis_agent.analyze_sales_funnel()
        summary["sections"]["funnel_analysis"] = funnel
        
        trend = await self.analysis_agent.analyze_sales_trend()
        summary["sections"]["trend_analysis"] = trend
        
        lost = await self.analysis_agent.analyze_lost_deals()
        summary["sections"]["lost_analysis"] = lost
        
        goal_progress = await self.notification_agent.check_goal_progress()
        summary["sections"]["goal_progress"] = goal_progress
        
        summary["recommendations"] = []
        
        if funnel.get("bottlenecks"):
            summary["recommendations"].append({
                "priority": "high",
                "area": "销售漏斗",
                "recommendation": f"发现 {len(funnel['bottlenecks'])} 个转化瓶颈，建议重点优化"
            })
        
        if trend.get("trend_direction") == "下降":
            summary["recommendations"].append({
                "priority": "high",
                "area": "销售趋势",
                "recommendation": f"销售额呈下降趋势 ({trend['change_rate']}%)，需要制定提升策略"
            })
        
        if lost.get("total_lost", 0) > 3:
            summary["recommendations"].append({
                "priority": "medium",
                "area": "丢单分析",
                "recommendation": f"本周丢失 {lost['total_lost']} 个机会，建议分析原因并改进"
            })
        
        for goal in goal_progress:
            if goal.get("status") == "at_risk":
                summary["recommendations"].append({
                    "priority": "high",
                    "area": "目标管理",
                    "recommendation": goal.get("message", "")
                })
        
        await self.memory_service.store(
            content=f"周度总结: 成交{weekly_report['metrics']['won_opportunities']}单，金额{weekly_report['metrics']['won_amount']}元",
            memory_type="episodic",
            entity_type="report",
            title="周度总结报告",
            importance=0.8
        )
        
        return summary
    
    async def coordinate_task(
        self,
        task_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        协调执行任务
        """
        coordination_result = {
            "task_type": task_type,
            "started_at": datetime.now().isoformat(),
            "steps": []
        }
        
        try:
            if task_type == "customer_engagement":
                customer_id = params.get("customer_id")
                
                analysis = await self.analysis_agent.analyze_customer_value(customer_id)
                coordination_result["steps"].append({
                    "agent": "analysis",
                    "action": "customer_value_analysis",
                    "result": analysis
                })
                
                task = await self.execution_agent.schedule_followup(
                    customer_id=customer_id,
                    content=params.get("content", "定期客户维护"),
                    next_action=params.get("next_action"),
                    next_date=params.get("next_date")
                )
                coordination_result["steps"].append({
                    "agent": "execution",
                    "action": "schedule_followup",
                    "task_id": task.id
                })
                
                await self.memory_service.store_interaction(
                    entity_type="customer",
                    entity_id=customer_id,
                    interaction_type="engagement_workflow",
                    content=f"执行客户互动工作流: {params.get('content', '')}"
                )
            
            elif task_type == "opportunity_advancement":
                opportunity_id = params.get("opportunity_id")
                
                risk = await self.analysis_agent.analyze_opportunity_risk(opportunity_id)
                coordination_result["steps"].append({
                    "agent": "analysis",
                    "action": "risk_analysis",
                    "result": risk
                })
                
                if risk.get("risks"):
                    for r in risk["risks"]:
                        if r["type"] == "stagnation":
                            task = await self.execution_agent.create_task(
                                task_type="create_followup",
                                title=f"推进机会: {risk['opportunity_name']}",
                                action_plan={
                                    "opportunity_id": opportunity_id,
                                    "content": "机会停滞，需要主动推进"
                                }
                            )
                            coordination_result["steps"].append({
                                "agent": "execution",
                                "action": "create_advancement_task",
                                "task_id": task.id
                            })
                            break
            
            elif task_type == "batch_customer_outreach":
                customer_ids = params.get("customer_ids", [])
                content = params.get("content", "")
                
                result = await self.execution_agent.batch_create_followups(
                    customer_ids=customer_ids,
                    content_template=content
                )
                coordination_result["steps"].append({
                    "agent": "execution",
                    "action": "batch_followups",
                    "result": result
                })
            
            coordination_result["success"] = True
            
        except Exception as e:
            coordination_result["success"] = False
            coordination_result["error"] = str(e)
            logger.error(f"任务协调失败: {e}")
        
        coordination_result["completed_at"] = datetime.now().isoformat()
        
        return coordination_result
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        获取所有Agent的状态
        """
        monitoring_status = {
            "name": "MonitoringAgent",
            "status": "active",
            "last_scan": datetime.now().isoformat(),
            "capabilities": [
                "客户流失预警",
                "机会停滞预警",
                "跟进逾期预警",
                "报价过期预警",
                "高价值机会提醒"
            ]
        }
        
        analysis_status = {
            "name": "AnalysisAgent",
            "status": "active",
            "capabilities": [
                "客户价值分析",
                "销售漏斗分析",
                "丢单原因分析",
                "销售趋势分析",
                "机会风险分析"
            ]
        }
        
        execution_status = {
            "name": "ExecutionAgent",
            "status": "active",
            "task_stats": await self.execution_agent.get_task_statistics()
        }
        
        notification_status = {
            "name": "NotificationAgent",
            "status": "active",
            "capabilities": [
                "今日提醒",
                "日报生成",
                "周报生成",
                "目标进度检查"
            ]
        }
        
        return {
            "supervisor": {
                "name": "AgentSupervisor",
                "status": "active",
                "agents_count": 4
            },
            "agents": [
                monitoring_status,
                analysis_status,
                execution_status,
                notification_status
            ]
        }
    
    async def smart_dispatch(
        self,
        user_request: str
    ) -> Dict[str, Any]:
        """
        智能分发用户请求
        """
        request_lower = user_request.lower()
        
        dispatch_result = {
            "request": user_request,
            "dispatched_to": [],
            "results": []
        }
        
        if any(kw in request_lower for kw in ["预警", "扫描", "监控", "风险"]):
            alerts = await self.monitoring_agent.scan_all()
            dispatch_result["dispatched_to"].append("MonitoringAgent")
            dispatch_result["results"].append({
                "agent": "MonitoringAgent",
                "action": "scan_all",
                "alerts_found": len(alerts)
            })
        
        if any(kw in request_lower for kw in ["分析", "报告", "统计", "趋势"]):
            insights = await self.analysis_agent.generate_sales_insights()
            dispatch_result["dispatched_to"].append("AnalysisAgent")
            dispatch_result["results"].append({
                "agent": "AnalysisAgent",
                "action": "generate_insights",
                "insights": insights
            })
        
        if any(kw in request_lower for kw in ["提醒", "今日", "待办", "跟进"]):
            reminders = await self.notification_agent.get_today_reminders()
            dispatch_result["dispatched_to"].append("NotificationAgent")
            dispatch_result["results"].append({
                "agent": "NotificationAgent",
                "action": "get_reminders",
                "reminders": reminders
            })
        
        if any(kw in request_lower for kw in ["执行", "创建", "更新", "任务"]):
            pending = await self.execution_agent.get_pending_tasks()
            dispatch_result["dispatched_to"].append("ExecutionAgent")
            dispatch_result["results"].append({
                "agent": "ExecutionAgent",
                "action": "get_pending_tasks",
                "pending_count": len(pending)
            })
        
        if not dispatch_result["dispatched_to"]:
            status = await self.get_agent_status()
            dispatch_result["dispatched_to"].append("Supervisor")
            dispatch_result["results"].append({
                "agent": "Supervisor",
                "action": "get_status",
                "status": status
            })
        
        return dispatch_result
