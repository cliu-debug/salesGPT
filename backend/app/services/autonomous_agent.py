"""
自主决策Agent服务 - AI自主感知、决策和执行
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from app.models.models import (
    Customer, Opportunity, Quote, FollowUp,
    AgentTask, AgentMemory, AgentAlert, AgentGoal,
    TaskStatus, TaskPriority
)
from app.services.ai_service import ai_service
from app.services.memory_service import MemoryService
from app.services.monitoring_agent import MonitoringAgent
from app.services.analysis_agent import AnalysisAgent
from app.services.execution_agent import ExecutionAgent
from app.services.notification_agent import NotificationAgent
from app.core.logger import logger


class DecisionType(str, Enum):
    FOLLOWUP_CUSTOMER = "followup_customer"
    ADVANCE_OPPORTUNITY = "advance_opportunity"
    CREATE_QUOTE = "create_quote"
    UPDATE_STATUS = "update_status"
    ESCALATE_ALERT = "escalate_alert"
    BATCH_OUTREACH = "batch_outreach"
    GOAL_ADJUSTMENT = "goal_adjustment"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutonomousAgent:
    """
    自主决策Agent - 具备感知、决策、执行能力的智能体
    
    核心能力:
    1. 自主感知 - 持续监控销售状态，发现需要关注的事件
    2. 智能决策 - 分析情况，制定最优行动方案
    3. 风险评估 - 评估行动风险，决定是否需要人工确认
    4. 自主执行 - 低风险行动自动执行，高风险行动请求确认
    5. 学习优化 - 从结果中学习，持续优化决策
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)
        self.monitoring_agent = MonitoringAgent(db)
        self.analysis_agent = AnalysisAgent(db)
        self.execution_agent = ExecutionAgent(db)
        self.notification_agent = NotificationAgent(db)
        
        self.auto_execute_threshold = RiskLevel.LOW
        self.human_confirm_threshold = RiskLevel.MEDIUM
    
    async def perceive(self) -> Dict[str, Any]:
        """
        感知当前状态
        """
        perception = {
            "timestamp": datetime.now().isoformat(),
            "alerts": [],
            "opportunities": [],
            "customers": [],
            "goals": [],
            "tasks": []
        }
        
        alerts = await self.monitoring_agent.get_active_alerts(limit=10)
        perception["alerts"] = [
            {
                "id": a.id,
                "type": a.alert_type,
                "severity": a.severity,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "entity_name": a.entity_name,
                "description": a.description
            }
            for a in alerts
        ]
        
        stalled_query = select(Opportunity).where(
            and_(
                Opportunity.stage.notin_(["closed_won", "closed_lost"]),
                Opportunity.updated_at < datetime.now() - timedelta(days=7)
            )
        ).order_by(desc(Opportunity.amount)).limit(5)
        
        stalled_result = await self.db.execute(stalled_query)
        stalled_opps = stalled_result.scalars().all()
        
        perception["opportunities"] = [
            {
                "id": o.id,
                "name": o.name,
                "amount": o.amount,
                "stage": o.stage,
                "probability": o.probability,
                "customer_name": o.customer_name,
                "days_stalled": (datetime.now() - o.updated_at).days
            }
            for o in stalled_opps
        ]
        
        stale_customers_query = select(Customer).where(
            and_(
                Customer.status.in_(["interested", "negotiating"]),
                Customer.updated_at < datetime.now() - timedelta(days=14)
            )
        ).limit(5)
        
        stale_result = await self.db.execute(stale_customers_query)
        stale_customers = stale_result.scalars().all()
        
        perception["customers"] = [
            {
                "id": c.id,
                "name": c.name,
                "company": c.company,
                "status": c.status,
                "days_since_contact": (datetime.now() - c.updated_at).days
            }
            for c in stale_customers
        ]
        
        goals_query = select(AgentGoal).where(AgentGoal.status == "active")
        goals_result = await self.db.execute(goals_query)
        goals = goals_result.scalars().all()
        
        perception["goals"] = [
            {
                "id": g.id,
                "name": g.name,
                "target_value": g.target_value,
                "current_value": g.current_value,
                "progress": (g.current_value / g.target_value * 100) if g.target_value > 0 else 0,
                "end_date": g.end_date
            }
            for g in goals
        ]
        
        pending_tasks = await self.execution_agent.get_pending_tasks(limit=5)
        perception["tasks"] = [
            {
                "id": t.id,
                "type": t.task_type,
                "title": t.title,
                "priority": t.priority,
                "scheduled_at": t.scheduled_at
            }
            for t in pending_tasks
        ]
        
        return perception
    
    async def decide(
        self,
        perception: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        根据感知结果制定决策
        """
        decisions = []
        
        for alert in perception.get("alerts", []):
            decision = await self._decide_for_alert(alert)
            if decision:
                decisions.append(decision)
        
        for opp in perception.get("opportunities", []):
            decision = await self._decide_for_opportunity(opp)
            if decision:
                decisions.append(decision)
        
        for customer in perception.get("customers", []):
            decision = await self._decide_for_customer(customer)
            if decision:
                decisions.append(decision)
        
        for goal in perception.get("goals", []):
            decision = await self._decide_for_goal(goal)
            if decision:
                decisions.append(decision)
        
        decisions.sort(key=lambda x: self._priority_score(x), reverse=True)
        
        return decisions[:5]
    
    async def _decide_for_alert(
        self,
        alert: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        为预警制定决策
        """
        if alert["type"] == "customer_churn_risk":
            return {
                "decision_type": DecisionType.FOLLOWUP_CUSTOMER,
                "priority": "high" if alert["severity"] == "high" else "medium",
                "target": {
                    "type": "customer",
                    "id": alert["entity_id"],
                    "name": alert["entity_name"]
                },
                "action": "主动联系客户",
                "reason": f"客户流失风险: {alert['description']}",
                "risk_level": RiskLevel.LOW.value,
                "auto_executable": True,
                "action_plan": {
                    "customer_id": alert["entity_id"],
                    "content": f"客户流失预警跟进 - {alert['description']}",
                    "next_action": "了解客户最新需求和意向"
                }
            }
        
        elif alert["type"] == "opportunity_stalled":
            return {
                "decision_type": DecisionType.ADVANCE_OPPORTUNITY,
                "priority": "high",
                "target": {
                    "type": "opportunity",
                    "id": alert["entity_id"],
                    "name": alert["entity_name"]
                },
                "action": "推进停滞的机会",
                "reason": f"机会停滞: {alert['description']}",
                "risk_level": RiskLevel.MEDIUM.value,
                "auto_executable": False,
                "action_plan": {
                    "opportunity_id": alert["entity_id"],
                    "analysis_needed": True
                }
            }
        
        elif alert["type"] == "followup_overdue":
            return {
                "decision_type": DecisionType.FOLLOWUP_CUSTOMER,
                "priority": "medium",
                "target": {
                    "type": "followup",
                    "id": alert["entity_id"],
                    "name": alert["entity_name"]
                },
                "action": "执行逾期跟进",
                "reason": f"跟进逾期: {alert['description']}",
                "risk_level": RiskLevel.LOW.value,
                "auto_executable": True,
                "action_plan": {}
            }
        
        return None
    
    async def _decide_for_opportunity(
        self,
        opp: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        为机会制定决策
        """
        if opp.get("days_stalled", 0) > 7:
            risk_analysis = await self.analysis_agent.analyze_opportunity_risk(opp["id"])
            
            return {
                "decision_type": DecisionType.ADVANCE_OPPORTUNITY,
                "priority": "high" if opp.get("amount", 0) > 50000 else "medium",
                "target": {
                    "type": "opportunity",
                    "id": opp["id"],
                    "name": opp["name"]
                },
                "action": "分析并推进停滞机会",
                "reason": f"机会已停滞 {opp['days_stalled']} 天",
                "risk_level": RiskLevel.MEDIUM.value,
                "auto_executable": False,
                "action_plan": {
                    "opportunity_id": opp["id"],
                    "risk_analysis": risk_analysis
                }
            }
        
        return None
    
    async def _decide_for_customer(
        self,
        customer: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        为客户制定决策
        """
        days = customer.get("days_since_contact", 0)
        
        if days > 14:
            return {
                "decision_type": DecisionType.FOLLOWUP_CUSTOMER,
                "priority": "medium",
                "target": {
                    "type": "customer",
                    "id": customer["id"],
                    "name": customer["name"]
                },
                "action": "定期客户维护",
                "reason": f"客户已 {days} 天未联系",
                "risk_level": RiskLevel.LOW.value,
                "auto_executable": True,
                "action_plan": {
                    "customer_id": customer["id"],
                    "content": f"定期客户维护跟进 - 已{days}天未联系",
                    "next_action": "了解客户最新情况"
                }
            }
        
        return None
    
    async def _decide_for_goal(
        self,
        goal: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        为目标制定决策
        """
        progress = goal.get("progress", 0)
        
        if goal.get("end_date"):
            days_remaining = (goal["end_date"] - datetime.now().date()).days
            
            if days_remaining <= 7 and progress < 70:
                return {
                    "decision_type": DecisionType.GOAL_ADJUSTMENT,
                    "priority": "high",
                    "target": {
                        "type": "goal",
                        "id": goal["id"],
                        "name": goal["name"]
                    },
                    "action": "目标达成预警",
                    "reason": f"目标剩余{days_remaining}天，进度仅{progress:.0f}%",
                    "risk_level": RiskLevel.HIGH.value,
                    "auto_executable": False,
                    "action_plan": {
                        "goal_id": goal["id"],
                        "current_progress": progress,
                        "days_remaining": days_remaining
                    }
                }
        
        return None
    
    def _priority_score(self, decision: Dict[str, Any]) -> int:
        """
        计算决策优先级分数
        """
        score = 0
        
        priority_map = {"high": 30, "medium": 20, "low": 10}
        score += priority_map.get(decision.get("priority", "medium"), 10)
        
        risk_map = {"critical": 40, "high": 30, "medium": 20, "low": 10}
        score += risk_map.get(decision.get("risk_level", "medium"), 10)
        
        if decision.get("auto_executable"):
            score += 5
        
        return score
    
    async def assess_risk(
        self,
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        评估决策风险
        """
        risk_level = decision.get("risk_level", RiskLevel.MEDIUM.value)
        
        assessment = {
            "risk_level": risk_level,
            "factors": [],
            "mitigations": [],
            "requires_confirmation": False
        }
        
        if decision["decision_type"] == DecisionType.FOLLOWUP_CUSTOMER.value:
            assessment["factors"].append("客户联系频率")
            assessment["mitigations"].append("使用AI生成的专业话术")
        
        elif decision["decision_type"] == DecisionType.ADVANCE_OPPORTUNITY.value:
            assessment["factors"].append("机会金额大小")
            assessment["factors"].append("客户关系状态")
            assessment["mitigations"].append("先进行风险评估")
            assessment["requires_confirmation"] = True
        
        elif decision["decision_type"] == DecisionType.UPDATE_STATUS.value:
            assessment["factors"].append("状态变更影响")
            assessment["mitigations"].append("记录变更原因")
        
        elif decision["decision_type"] == DecisionType.GOAL_ADJUSTMENT.value:
            assessment["factors"].append("目标达成影响")
            assessment["requires_confirmation"] = True
        
        if risk_level in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]:
            assessment["requires_confirmation"] = True
        
        return assessment
    
    async def execute(
        self,
        decision: Dict[str, Any],
        auto_confirm: bool = False
    ) -> Dict[str, Any]:
        """
        执行决策
        """
        risk_assessment = await self.assess_risk(decision)
        
        if risk_assessment["requires_confirmation"] and not auto_confirm:
            return {
                "status": "pending_confirmation",
                "decision": decision,
                "risk_assessment": risk_assessment,
                "message": "此决策需要人工确认"
            }
        
        execution_result = {
            "decision_type": decision["decision_type"],
            "target": decision["target"],
            "started_at": datetime.now().isoformat(),
            "status": "executing"
        }
        
        try:
            if decision["decision_type"] == DecisionType.FOLLOWUP_CUSTOMER.value:
                result = await self._execute_followup(decision["action_plan"])
                execution_result["result"] = result
            
            elif decision["decision_type"] == DecisionType.ADVANCE_OPPORTUNITY.value:
                result = await self._execute_advance_opportunity(decision["action_plan"])
                execution_result["result"] = result
            
            elif decision["decision_type"] == DecisionType.GOAL_ADJUSTMENT.value:
                result = await self._execute_goal_adjustment(decision["action_plan"])
                execution_result["result"] = result
            
            execution_result["status"] = "completed"
            execution_result["completed_at"] = datetime.now().isoformat()
            
            await self._record_execution(decision, execution_result, success=True)
            
        except Exception as e:
            execution_result["status"] = "failed"
            execution_result["error"] = str(e)
            execution_result["completed_at"] = datetime.now().isoformat()
            
            await self._record_execution(decision, execution_result, success=False)
        
        return execution_result
    
    async def _execute_followup(
        self,
        action_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行跟进决策
        """
        customer_id = action_plan.get("customer_id")
        content = action_plan.get("content", "定期跟进")
        next_action = action_plan.get("next_action")
        
        task = await self.execution_agent.schedule_followup(
            customer_id=customer_id,
            content=content,
            next_action=next_action
        )
        
        return {
            "task_id": task.id,
            "message": "跟进任务已创建"
        }
    
    async def _execute_advance_opportunity(
        self,
        action_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行推进机会决策
        """
        opportunity_id = action_plan.get("opportunity_id")
        
        risk_analysis = await self.analysis_agent.analyze_opportunity_risk(opportunity_id)
        
        task = await self.execution_agent.create_task(
            task_type="create_followup",
            title=f"推进机会分析",
            target_entity_type="opportunity",
            target_entity_id=opportunity_id,
            action_plan={
                "opportunity_id": opportunity_id,
                "risk_analysis": risk_analysis
            }
        )
        
        return {
            "task_id": task.id,
            "risk_analysis": risk_analysis,
            "message": "机会分析任务已创建"
        }
    
    async def _execute_goal_adjustment(
        self,
        action_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行目标调整决策
        """
        goal_id = action_plan.get("goal_id")
        
        alert = AgentAlert(
            alert_type="goal_at_risk",
            severity="high",
            title="目标达成风险预警",
            description=f"目标进度落后，需要关注",
            entity_type="goal",
            entity_id=goal_id
        )
        
        self.db.add(alert)
        await self.db.commit()
        
        return {
            "alert_id": alert.id,
            "message": "目标风险预警已创建"
        }
    
    async def _record_execution(
        self,
        decision: Dict[str, Any],
        result: Dict[str, Any],
        success: bool
    ):
        """
        记录执行结果
        """
        await self.memory_service.store_interaction(
            entity_type=decision["target"]["type"],
            entity_id=decision["target"]["id"],
            interaction_type=f"autonomous_decision_{decision['decision_type']}",
            content=f"自主决策: {decision['action']} - {'成功' if success else '失败'}",
            outcome="success" if success else "failure"
        )
    
    async def run_autonomous_cycle(
        self,
        auto_execute: bool = False
    ) -> Dict[str, Any]:
        """
        执行完整的自主决策周期
        """
        cycle_start = datetime.now()
        
        cycle_result = {
            "cycle_id": f"cycle_{cycle_start.strftime('%Y%m%d%H%M%S')}",
            "started_at": cycle_start.isoformat(),
            "phases": {}
        }
        
        logger.info("开始自主决策周期...")
        
        perception = await self.perceive()
        cycle_result["phases"]["perception"] = {
            "status": "completed",
            "alerts_count": len(perception["alerts"]),
            "opportunities_count": len(perception["opportunities"]),
            "customers_count": len(perception["customers"])
        }
        
        decisions = await self.decide(perception)
        cycle_result["phases"]["decision"] = {
            "status": "completed",
            "decisions_count": len(decisions)
        }
        
        executions = []
        for decision in decisions:
            if auto_execute or decision.get("auto_executable", False):
                result = await self.execute(decision, auto_confirm=auto_execute)
                executions.append(result)
            else:
                executions.append({
                    "status": "pending_confirmation",
                    "decision": decision
                })
        
        cycle_result["phases"]["execution"] = {
            "status": "completed",
            "executions_count": len(executions),
            "results": executions
        }
        
        cycle_end = datetime.now()
        cycle_result["completed_at"] = cycle_end.isoformat()
        cycle_result["duration_seconds"] = (cycle_end - cycle_start).total_seconds()
        
        cycle_result["summary"] = {
            "perceived_items": len(perception["alerts"]) + len(perception["opportunities"]) + len(perception["customers"]),
            "decisions_made": len(decisions),
            "actions_executed": len([e for e in executions if e.get("status") == "completed"]),
            "pending_confirmations": len([e for e in executions if e.get("status") == "pending_confirmation"])
        }
        
        await self.memory_service.store(
            content=f"自主决策周期完成: 感知{cycle_result['summary']['perceived_items']}项, 决策{cycle_result['summary']['decisions_made']}项, 执行{cycle_result['summary']['actions_executed']}项",
            memory_type="episodic",
            entity_type="autonomous_cycle",
            title=f"自主决策周期 {cycle_result['cycle_id']}",
            importance=0.8
        )
        
        logger.info(f"自主决策周期完成: {cycle_result['summary']}")
        
        return cycle_result
    
    async def get_pending_decisions(self) -> List[Dict[str, Any]]:
        """
        获取待确认的决策
        """
        perception = await self.perceive()
        decisions = await self.decide(perception)
        
        pending = []
        for decision in decisions:
            risk = await self.assess_risk(decision)
            if risk["requires_confirmation"]:
                pending.append({
                    "decision": decision,
                    "risk_assessment": risk
                })
        
        return pending
    
    async def confirm_and_execute(
        self,
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        确认并执行决策
        """
        return await self.execute(decision, auto_confirm=True)
    
    async def reject_decision(
        self,
        decision: Dict[str, Any],
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        拒绝决策
        """
        await self.memory_service.store(
            content=f"决策被拒绝: {decision['action']} - 原因: {reason}",
            memory_type="episodic",
            entity_type=decision["target"]["type"],
            entity_id=decision["target"]["id"],
            title="决策拒绝记录",
            importance=0.6
        )
        
        return {
            "status": "rejected",
            "decision": decision,
            "reason": reason
        }
    
    async def learn_from_feedback(
        self,
        decision_id: str,
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从反馈中学习
        """
        await self.memory_service.store_knowledge(
            entity_type="decision",
            entity_id=int(decision_id[-8:], 16) % 10000000 if len(decision_id) >= 8 else 0,
            knowledge_type="feedback",
            content=f"决策反馈: {feedback.get('outcome', 'unknown')} - {feedback.get('comment', '')}",
            importance=0.9 if feedback.get("outcome") == "negative" else 0.5
        )
        
        return {
            "status": "learned",
            "feedback_recorded": True
        }
