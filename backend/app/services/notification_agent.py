"""
提醒Agent服务 - 发送通知和提醒
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from app.models.models import (
    Customer, Opportunity, Quote, FollowUp,
    AgentTask, AgentMemory, AgentAlert,
    TaskPriority
)
from app.services.memory_service import MemoryService
from app.core.logger import logger


class NotificationAgent:
    """
    提醒Agent - 发送通知和提醒
    
    提醒类型:
    1. 跟进提醒 - 今日待办、逾期任务
    2. 预警提醒 - 客户流失风险、机会停滞
    3. 目标提醒 - 目标进度、达成预警
    4. 报价提醒 - 报价过期、待跟进
    5. 日报/周报 - 销售数据汇总
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)
    
    async def get_today_reminders(self) -> Dict[str, Any]:
        """
        获取今日提醒
        """
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59)
        
        followups_query = select(FollowUp).where(
            and_(
                FollowUp.next_date >= today_start,
                FollowUp.next_date <= today_end
            )
        ).order_by(FollowUp.next_date)
        
        followups_result = await self.db.execute(followups_query)
        today_followups = followups_result.scalars().all()
        
        alerts_query = select(AgentAlert).where(
            AgentAlert.is_resolved == False,
            AgentAlert.is_read == False
        ).order_by(desc(AgentAlert.severity), desc(AgentAlert.created_at)).limit(5)
        
        alerts_result = await self.db.execute(alerts_query)
        unread_alerts = alerts_result.scalars().all()
        
        expiring_quotes_query = select(Quote).where(
            and_(
                Quote.status == "sent",
                Quote.valid_until != None,
                Quote.valid_until <= (now + timedelta(days=3)).date()
            )
        )
        
        expiring_quotes_result = await self.db.execute(expiring_quotes_query)
        expiring_quotes = expiring_quotes_result.scalars().all()
        
        reminders = {
            "date": now.strftime("%Y-%m-%d"),
            "followups": [
                {
                    "id": f.id,
                    "customer_name": f.customer_name,
                    "next_action": f.next_action,
                    "next_date": f.next_date,
                    "time": f.next_date.strftime("%H:%M") if f.next_date else ""
                }
                for f in today_followups
            ],
            "alerts": [
                {
                    "id": a.id,
                    "type": a.alert_type,
                    "severity": a.severity,
                    "title": a.title,
                    "entity_name": a.entity_name
                }
                for a in unread_alerts
            ],
            "expiring_quotes": [
                {
                    "id": q.id,
                    "customer_name": q.customer_name,
                    "total_amount": q.total_amount,
                    "valid_until": q.valid_until
                }
                for q in expiring_quotes
            ],
            "summary": {
                "total_followups": len(today_followups),
                "unread_alerts": len(unread_alerts),
                "expiring_quotes": len(expiring_quotes)
            }
        }
        
        return reminders
    
    async def generate_daily_report(self) -> Dict[str, Any]:
        """
        生成日报
        """
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        new_customers_query = select(func.count(Customer.id)).where(
            Customer.created_at >= today_start
        )
        new_customers_result = await self.db.execute(new_customers_query)
        new_customers = new_customers_result.scalar() or 0
        
        won_opps_query = select(
            func.count(Opportunity.id).label('count'),
            func.sum(Opportunity.amount).label('amount')
        ).where(
            Opportunity.stage == "closed_won",
            Opportunity.updated_at >= today_start
        )
        won_result = await self.db.execute(won_opps_query)
        won_row = won_result.one()
        won_count = won_row.count or 0
        won_amount = won_row.amount or 0
        
        new_opps_query = select(
            func.count(Opportunity.id).label('count'),
            func.sum(Opportunity.amount).label('amount')
        ).where(
            Opportunity.created_at >= today_start
        )
        new_opps_result = await self.db.execute(new_opps_query)
        new_opps_row = new_opps_result.one()
        new_opps_count = new_opps_row.count or 0
        new_opps_amount = new_opps_row.amount or 0
        
        followups_query = select(func.count(FollowUp.id)).where(
            FollowUp.created_at >= today_start
        )
        followups_result = await self.db.execute(followups_query)
        followups_count = followups_result.scalar() or 0
        
        quotes_query = select(
            func.count(Quote.id).label('count'),
            func.sum(Quote.total_amount).label('amount')
        ).where(
            Quote.created_at >= today_start
        )
        quotes_result = await self.db.execute(quotes_query)
        quotes_row = quotes_result.one()
        quotes_count = quotes_row.count or 0
        quotes_amount = quotes_row.amount or 0
        
        alerts_query = select(func.count(AgentAlert.id)).where(
            AgentAlert.created_at >= today_start
        )
        alerts_result = await self.db.execute(alerts_query)
        new_alerts = alerts_result.scalar() or 0
        
        report = {
            "report_type": "daily",
            "date": now.strftime("%Y-%m-%d"),
            "generated_at": now.isoformat(),
            "metrics": {
                "new_customers": new_customers,
                "won_opportunities": won_count,
                "won_amount": won_amount,
                "new_opportunities": new_opps_count,
                "new_opportunities_amount": new_opps_amount,
                "followups_created": followups_count,
                "quotes_created": quotes_count,
                "quotes_amount": quotes_amount,
                "new_alerts": new_alerts
            },
            "highlights": [],
            "concerns": [],
            "recommendations": []
        }
        
        if won_amount > 0:
            report["highlights"].append(f"今日成交 {won_count} 单，金额 {won_amount/10000:.1f} 万元")
        
        if new_customers > 0:
            report["highlights"].append(f"新增 {new_customers} 个客户")
        
        if new_alerts > 0:
            report["concerns"].append(f"发现 {new_alerts} 条新预警需要处理")
        
        if won_count == 0:
            report["recommendations"].append("今日暂无成交，建议重点跟进高概率机会")
        
        if followups_count == 0:
            report["recommendations"].append("今日未创建跟进记录，建议及时记录客户互动")
        
        return report
    
    async def generate_weekly_report(self) -> Dict[str, Any]:
        """
        生成周报
        """
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        new_customers_query = select(func.count(Customer.id)).where(
            Customer.created_at >= week_start
        )
        new_customers_result = await self.db.execute(new_customers_query)
        new_customers = new_customers_result.scalar() or 0
        
        won_opps_query = select(
            func.count(Opportunity.id).label('count'),
            func.sum(Opportunity.amount).label('amount')
        ).where(
            Opportunity.stage == "closed_won",
            Opportunity.updated_at >= week_start
        )
        won_result = await self.db.execute(won_opps_query)
        won_row = won_result.one()
        won_count = won_row.count or 0
        won_amount = won_row.amount or 0
        
        lost_opps_query = select(
            func.count(Opportunity.id).label('count'),
            func.sum(Opportunity.amount).label('amount')
        ).where(
            Opportunity.stage == "closed_lost",
            Opportunity.updated_at >= week_start
        )
        lost_result = await self.db.execute(lost_opps_query)
        lost_row = lost_result.one()
        lost_count = lost_row.count or 0
        lost_amount = lost_row.amount or 0
        
        active_opps_query = select(
            func.count(Opportunity.id).label('count'),
            func.sum(Opportunity.amount).label('amount')
        ).where(
            Opportunity.stage.notin_(["closed_won", "closed_lost"])
        )
        active_result = await self.db.execute(active_opps_query)
        active_row = active_result.one()
        active_count = active_row.count or 0
        active_amount = active_row.amount or 0
        
        followups_query = select(func.count(FollowUp.id)).where(
            FollowUp.created_at >= week_start
        )
        followups_result = await self.db.execute(followups_query)
        followups_count = followups_result.scalar() or 0
        
        win_rate = won_count / (won_count + lost_count) * 100 if (won_count + lost_count) > 0 else 0
        
        report = {
            "report_type": "weekly",
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": now.strftime("%Y-%m-%d"),
            "generated_at": now.isoformat(),
            "metrics": {
                "new_customers": new_customers,
                "won_opportunities": won_count,
                "won_amount": won_amount,
                "lost_opportunities": lost_count,
                "lost_amount": lost_amount,
                "win_rate": round(win_rate, 1),
                "active_opportunities": active_count,
                "pipeline_amount": active_amount,
                "followups_created": followups_count
            },
            "highlights": [],
            "concerns": [],
            "recommendations": []
        }
        
        if won_amount > 0:
            report["highlights"].append(f"本周成交 {won_count} 单，金额 {won_amount/10000:.1f} 万元")
        
        if new_customers > 3:
            report["highlights"].append(f"新增 {new_customers} 个客户，客户开发积极")
        
        if win_rate < 30 and (won_count + lost_count) > 0:
            report["concerns"].append(f"成交率仅 {win_rate:.0f}%，需要优化销售策略")
        
        if lost_amount > 0:
            report["concerns"].append(f"本周丢失 {lost_count} 个机会，金额 {lost_amount/10000:.1f} 万元")
        
        if active_amount > 0:
            report["recommendations"].append(f"当前漏斗价值 {active_amount/10000:.1f} 万元，重点推进高概率机会")
        
        if followups_count < 5:
            report["recommendations"].append("本周跟进次数较少，建议增加客户互动")
        
        return report
    
    async def check_goal_progress(self) -> List[Dict[str, Any]]:
        """
        检查目标进度
        """
        from app.models.models import AgentGoal
        
        query = select(AgentGoal).where(
            AgentGoal.status == "active"
        )
        result = await self.db.execute(query)
        goals = result.scalars().all()
        
        notifications = []
        
        for goal in goals:
            progress = (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0
            
            if goal.end_date:
                days_remaining = (goal.end_date - datetime.now().date()).days
            else:
                days_remaining = None
            
            notification = {
                "goal_id": goal.id,
                "goal_name": goal.name,
                "current_value": goal.current_value,
                "target_value": goal.target_value,
                "progress": round(progress, 1),
                "days_remaining": days_remaining,
                "status": "on_track",
                "message": ""
            }
            
            if progress >= 100:
                notification["status"] = "completed"
                notification["message"] = f"🎉 恭喜！目标「{goal.name}」已达成！"
            elif progress >= 80:
                notification["status"] = "almost_there"
                notification["message"] = f"目标「{goal.name}」即将达成，还差 {goal.target_value - goal.current_value:.0f} {goal.unit}"
            elif days_remaining is not None and days_remaining <= 7 and progress < 70:
                notification["status"] = "at_risk"
                notification["message"] = f"⚠️ 目标「{goal.name}」进度落后，剩余 {days_remaining} 天，当前进度 {progress:.0f}%"
            elif progress < 50:
                notification["status"] = "behind"
                notification["message"] = f"目标「{goal.name}」进度过半，需要加速推进"
            else:
                notification["message"] = f"目标「{goal.name}」进度正常，已完成 {progress:.0f}%"
            
            notifications.append(notification)
        
        return notifications
    
    async def send_followup_reminder(
        self,
        followup_id: int
    ) -> Dict[str, Any]:
        """
        发送跟进提醒
        """
        query = select(FollowUp).where(FollowUp.id == followup_id)
        result = await self.db.execute(query)
        followup = result.scalar_one_or_none()
        
        if not followup:
            return {"success": False, "error": "跟进任务不存在"}
        
        reminder = {
            "type": "followup_reminder",
            "followup_id": followup_id,
            "customer_name": followup.customer_name,
            "next_action": followup.next_action,
            "next_date": followup.next_date.isoformat() if followup.next_date else None,
            "message": f"提醒：请跟进客户 {followup.customer_name}，行动：{followup.next_action}",
            "sent_at": datetime.now().isoformat()
        }
        
        logger.info(f"发送跟进提醒: {reminder}")
        
        await self.memory_service.store_interaction(
            entity_type="followup",
            entity_id=followup_id,
            interaction_type="reminder_sent",
            content=f"发送跟进提醒: {followup.next_action}"
        )
        
        return {
            "success": True,
            "reminder": reminder
        }
    
    async def send_alert_notification(
        self,
        alert_id: int
    ) -> Dict[str, Any]:
        """
        发送预警通知
        """
        query = select(AgentAlert).where(AgentAlert.id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            return {"success": False, "error": "预警不存在"}
        
        notification = {
            "type": "alert_notification",
            "alert_id": alert_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "suggested_action": alert.suggested_action,
            "message": f"[{alert.severity.upper()}] {alert.title}",
            "sent_at": datetime.now().isoformat()
        }
        
        logger.info(f"发送预警通知: {notification}")
        
        alert.is_read = True
        await self.db.commit()
        
        return {
            "success": True,
            "notification": notification
        }
    
    async def batch_send_reminders(
        self,
        reminder_type: str = "today_followups"
    ) -> Dict[str, Any]:
        """
        批量发送提醒
        """
        sent = []
        failed = []
        
        if reminder_type == "today_followups":
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59)
            
            query = select(FollowUp).where(
                and_(
                    FollowUp.next_date >= today_start,
                    FollowUp.next_date <= today_end
                )
            )
            
            result = await self.db.execute(query)
            followups = result.scalars().all()
            
            for followup in followups:
                try:
                    reminder_result = await self.send_followup_reminder(followup.id)
                    if reminder_result["success"]:
                        sent.append(followup.id)
                    else:
                        failed.append({"id": followup.id, "error": reminder_result["error"]})
                except Exception as e:
                    failed.append({"id": followup.id, "error": str(e)})
        
        return {
            "success": True,
            "reminder_type": reminder_type,
            "sent_count": len(sent),
            "failed_count": len(failed),
            "sent_ids": sent,
            "failed": failed
        }
    
    async def get_notification_history(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取通知历史
        """
        memories = await self.memory_service.recall(
            entity_type="notification",
            limit=limit
        )
        
        history = []
        for memory in memories:
            history.append({
                "id": memory.id,
                "type": memory.extra_data.get("notification_type", "unknown") if memory.extra_data else "unknown",
                "title": memory.title,
                "content": memory.content,
                "created_at": memory.created_at
            })
        
        return history
    
    async def create_smart_reminder(
        self,
        entity_type: str,
        entity_id: int,
        reminder_type: str,
        message: str,
        scheduled_time: datetime = None
    ) -> AgentTask:
        """
        创建智能提醒任务
        """
        from app.services.execution_agent import ExecutionAgent
        
        execution_agent = ExecutionAgent(self.db)
        
        task = await execution_agent.create_task(
            task_type="send_notification",
            title=f"提醒: {reminder_type}",
            description=message,
            target_entity_type=entity_type,
            target_entity_id=entity_id,
            action_plan={
                "notification_type": reminder_type,
                "content": message,
                "entity_type": entity_type,
                "entity_id": entity_id
            },
            scheduled_at=scheduled_time
        )
        
        return task
