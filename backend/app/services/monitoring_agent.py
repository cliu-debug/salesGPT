"""
监控Agent服务 - 主动监控销售数据并发现预警
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from app.models.models import (
    Customer, Opportunity, Quote, FollowUp,
    AgentAlert, AgentTask, AgentGoal,
    AlertType, TaskPriority, TaskStatus
)
from app.services.ai_service import ai_service
from app.core.logger import logger


class MonitoringAgent:
    """
    监控Agent - 持续扫描销售数据，发现需要关注的事件
    
    监控规则:
    1. 客户流失预警 - 长时间未联系的客户
    2. 机会停滞预警 - 长时间无进展的销售机会
    3. 跟进逾期预警 - 超过计划时间的跟进任务
    4. 报价过期预警 - 即将过期或已过期的报价单
    5. 高价值机会提醒 - 高金额的机会需要关注
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def scan_all(self, user: Any = None) -> List[AgentAlert]:
        """
        执行所有监控规则扫描
        
        Args:
            user: 当前用户（用于数据隔离）
        """
        alerts = []
        
        alerts.extend(await self.scan_customer_churn_risk(user=user))
        alerts.extend(await self.scan_stalled_opportunities(user=user))
        alerts.extend(await self.scan_overdue_followups(user=user))
        alerts.extend(await self.scan_expiring_quotes(user=user))
        alerts.extend(await self.scan_high_value_opportunities(user=user))
        
        logger.info(f"监控扫描完成，发现 {len(alerts)} 条预警")
        
        return alerts
    
    async def scan_customer_churn_risk(
        self,
        days_threshold: int = 14,
        user: Any = None
    ) -> List[AgentAlert]:
        """
        扫描客户流失风险
        - 超过N天未联系的客户
        
        Args:
            days_threshold: 天数阈值
            user: 当前用户（用于数据隔离）
        """
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        query = select(Customer).where(
            and_(
                Customer.status.in_(["potential", "interested", "negotiating"]),
                Customer.updated_at < cutoff_date
            )
        )
        
        # 数据隔离：普通用户只能看到自己组织的客户
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            query = query.where(Customer.organization_id == user.organization_id)
        
        result = await self.db.execute(query)
        customers = result.scalars().all()
        
        alerts = []
        for customer in customers:
            days_since_contact = (datetime.now() - customer.updated_at).days
            
            existing_alert = await self._check_existing_alert(
                AlertType.CUSTOMER_CHURN_RISK.value,
                "customer",
                customer.id
            )
            
            if existing_alert:
                continue
            
            severity = "high" if days_since_contact > 21 else "medium"
            
            alert = AgentAlert(
                alert_type=AlertType.CUSTOMER_CHURN_RISK.value,
                severity=severity,
                title=f"客户流失风险: {customer.name}",
                description=f"客户 {customer.name} 已 {days_since_contact} 天未联系，存在流失风险",
                entity_type="customer",
                entity_id=customer.id,
                entity_name=customer.name,
                suggested_action=f"建议立即联系客户，了解最新需求。可使用AI生成跟进话术。",
                metadata={
                    "days_since_contact": days_since_contact,
                    "customer_status": customer.status,
                    "last_updated": str(customer.updated_at)
                }
            )
            
            self.db.add(alert)
            alerts.append(alert)
        
        await self.db.commit()
        return alerts
    
    async def scan_stalled_opportunities(
        self,
        days_threshold: int = 7,
        user: Any = None
    ) -> List[AgentAlert]:
        """
        扫描停滞的销售机会
        - 超过N天无进展的机会
        
        Args:
            days_threshold: 天数阈值
            user: 当前用户（用于数据隔离）
        """
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        query = select(Opportunity).where(
            and_(
                Opportunity.stage.notin_(["closed_won", "closed_lost"]),
                Opportunity.updated_at < cutoff_date
            )
        )
        
        # 数据隔离：普通用户只能看到自己组织的机会
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            query = query.where(Opportunity.organization_id == user.organization_id)
        
        result = await self.db.execute(query)
        opportunities = result.scalars().all()
        
        alerts = []
        for opp in opportunities:
            days_stalled = (datetime.now() - opp.updated_at).days
            
            existing_alert = await self._check_existing_alert(
                AlertType.OPPORTUNITY_STALLED.value,
                "opportunity",
                opp.id
            )
            
            if existing_alert:
                continue
            
            severity = "high" if opp.amount and opp.amount > 50000 else "medium"
            
            alert = AgentAlert(
                alert_type=AlertType.OPPORTUNITY_STALLED.value,
                severity=severity,
                title=f"机会停滞: {opp.name}",
                description=f"销售机会「{opp.name}」已 {days_stalled} 天无进展，金额 {opp.amount or 0} 元",
                entity_type="opportunity",
                entity_id=opp.id,
                entity_name=opp.name,
                suggested_action="分析阻碍因素，制定推进策略，或调整预期成交概率",
                metadata={
                    "days_stalled": days_stalled,
                    "stage": opp.stage,
                    "amount": opp.amount,
                    "probability": opp.probability
                }
            )
            
            self.db.add(alert)
            alerts.append(alert)
        
        await self.db.commit()
        return alerts
    
    async def scan_overdue_followups(
        self,
        user: Any = None
    ) -> List[AgentAlert]:
        """
        扫描逾期的跟进任务
        
        Args:
            user: 当前用户（用于数据隔离）
        """
        query = select(FollowUp).where(
            and_(
                FollowUp.next_date < datetime.now(),
                FollowUp.next_action != None
            )
        )
        
        # 数据隔离：普通用户只能看到自己组织的跟进
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            query = query.where(FollowUp.organization_id == user.organization_id)
        
        result = await self.db.execute(query)
        followups = result.scalars().all()
        
        alerts = []
        for followup in followups:
            days_overdue = (datetime.now() - followup.next_date).days
            
            existing_alert = await self._check_existing_alert(
                AlertType.FOLLOWUP_OVERDUE.value,
                "followup",
                followup.id
            )
            
            if existing_alert:
                continue
            
            severity = "high" if days_overdue > 3 else "medium"
            
            alert = AgentAlert(
                alert_type=AlertType.FOLLOWUP_OVERDUE.value,
                severity=severity,
                title=f"跟进逾期: {followup.customer_name}",
                description=f"对客户 {followup.customer_name} 的跟进任务已逾期 {days_overdue} 天",
                entity_type="followup",
                entity_id=followup.id,
                entity_name=followup.customer_name,
                suggested_action="立即跟进或重新安排跟进时间",
                metadata={
                    "days_overdue": days_overdue,
                    "next_action": followup.next_action,
                    "scheduled_date": str(followup.next_date)
                }
            )
            
            self.db.add(alert)
            alerts.append(alert)
        
        await self.db.commit()
        return alerts
    
    async def scan_expiring_quotes(
        self,
        days_threshold: int = 3,
        user: Any = None
    ) -> List[AgentAlert]:
        """
        扫描即将过期的报价单
        
        Args:
            days_threshold: 天数阈值
            user: 当前用户（用于数据隔离）
        """
        now = datetime.now()
        threshold_date = now + timedelta(days=days_threshold)
        
        query = select(Quote).where(
            and_(
                Quote.status == "sent",
                Quote.valid_until != None,
                Quote.valid_until <= threshold_date.date()
            )
        )
        
        # 数据隔离：普通用户只能看到自己组织的报价
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            query = query.where(Quote.organization_id == user.organization_id)
        
        result = await self.db.execute(query)
        quotes = result.scalars().all()
        
        alerts = []
        for quote in quotes:
            days_to_expire = (quote.valid_until - now.date()).days if quote.valid_until else 0
            
            existing_alert = await self._check_existing_alert(
                AlertType.QUOTE_EXPIRING.value,
                "quote",
                quote.id
            )
            
            if existing_alert:
                continue
            
            severity = "high" if days_to_expire <= 0 else "medium"
            title = f"报价{'已过期' if days_to_expire <= 0 else '即将过期'}: {quote.customer_name}"
            
            alert = AgentAlert(
                alert_type=AlertType.QUOTE_EXPIRING.value,
                severity=severity,
                title=title,
                description=f"报价单 #{quote.id} ({quote.customer_name}) {'已过期' if days_to_expire <= 0 else f'{days_to_expire}天后过期'}，金额 {quote.total_amount} 元",
                entity_type="quote",
                entity_id=quote.id,
                entity_name=f"#{quote.id} - {quote.customer_name}",
                suggested_action="跟进报价状态，考虑延期或重新报价",
                metadata={
                    "days_to_expire": days_to_expire,
                    "total_amount": quote.total_amount,
                    "valid_until": str(quote.valid_until)
                }
            )
            
            self.db.add(alert)
            alerts.append(alert)
        
        await self.db.commit()
        return alerts
    
    async def scan_high_value_opportunities(
        self,
        amount_threshold: float = 100000,
        user: Any = None
    ) -> List[AgentAlert]:
        """
        扫描高价值机会
        
        Args:
            amount_threshold: 金额阈值
            user: 当前用户（用于数据隔离）
        """
        query = select(Opportunity).where(
            and_(
                Opportunity.amount >= amount_threshold,
                Opportunity.stage.notin_(["closed_won", "closed_lost"])
            )
        )
        
        # 数据隔离：普通用户只能看到自己组织的机会
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            query = query.where(Opportunity.organization_id == user.organization_id)
        
        result = await self.db.execute(query)
        opportunities = result.scalars().all()
        
        alerts = []
        for opp in opportunities:
            existing_alert = await self._check_existing_alert(
                AlertType.HIGH_VALUE_OPPORTUNITY.value,
                "opportunity",
                opp.id,
                max_age_hours=168
            )
            
            if existing_alert:
                continue
            
            alert = AgentAlert(
                alert_type=AlertType.HIGH_VALUE_OPPORTUNITY.value,
                severity="high",
                title=f"高价值机会: {opp.name}",
                description=f"发现高价值销售机会「{opp.name}」，金额 {opp.amount} 元，当前阶段: {opp.stage}",
                entity_type="opportunity",
                entity_id=opp.id,
                entity_name=opp.name,
                suggested_action="重点关注，制定专项跟进策略，确保成交",
                metadata={
                    "amount": opp.amount,
                    "stage": opp.stage,
                    "probability": opp.probability,
                    "customer_name": opp.customer_name
                }
            )
            
            self.db.add(alert)
            alerts.append(alert)
        
        await self.db.commit()
        return alerts
    
    async def _check_existing_alert(
        self,
        alert_type: str,
        entity_type: str,
        entity_id: int,
        max_age_hours: int = 48
    ) -> Optional[AgentAlert]:
        """
        检查是否已存在相同预警
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        query = select(AgentAlert).where(
            and_(
                AgentAlert.alert_type == alert_type,
                AgentAlert.entity_type == entity_type,
                AgentAlert.entity_id == entity_id,
                AgentAlert.is_resolved == False,
                AgentAlert.created_at >= cutoff_time
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_alerts(
        self,
        severity: Optional[str] = None,
        limit: int = 20,
        user: Any = None
    ) -> List[AgentAlert]:
        """
        获取活跃的预警列表
        
        Args:
            severity: 严重级别筛选
            limit: 返回数量限制
            user: 当前用户（用于数据隔离）
        """
        query = select(AgentAlert).where(
            AgentAlert.is_resolved == False
        )
        
        # 数据隔离：普通用户只能看到自己组织的预警
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            query = query.where(AgentAlert.organization_id == user.organization_id)
        
        if severity:
            query = query.where(AgentAlert.severity == severity)
        
        query = query.order_by(
            desc(AgentAlert.severity),
            desc(AgentAlert.created_at)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def resolve_alert(
        self,
        alert_id: int,
        action_taken: Optional[str] = None,
        resolved_by: Optional[str] = None
    ) -> Optional[AgentAlert]:
        """
        解决预警
        """
        query = select(AgentAlert).where(AgentAlert.id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalar_one_or_none()
        
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.now()
            alert.resolved_by = resolved_by or "system"
            alert.action_taken = action_taken
            await self.db.commit()
            await self.db.refresh(alert)
        
        return alert
    
    async def get_alert_summary(self, user: Any = None) -> Dict[str, Any]:
        """
        获取预警摘要统计
        
        Args:
            user: 当前用户（用于数据隔离）
        """
        total_query = select(func.count()).select_from(AgentAlert).where(
            AgentAlert.is_resolved == False
        )
        
        # 数据隔离
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            total_query = total_query.where(AgentAlert.organization_id == user.organization_id)
        
        total_result = await self.db.execute(total_query)
        total = total_result.scalar()
        
        severity_query = select(
            AgentAlert.severity,
            func.count().label('count')
        ).where(
            AgentAlert.is_resolved == False
        )
        
        # 数据隔离
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            severity_query = severity_query.where(AgentAlert.organization_id == user.organization_id)
        
        severity_query = severity_query.group_by(AgentAlert.severity)
        
        severity_result = await self.db.execute(severity_query)
        severity_distribution = {row.severity: row.count for row in severity_result}
        
        type_query = select(
            AgentAlert.alert_type,
            func.count().label('count')
        ).where(
            AgentAlert.is_resolved == False
        )
        
        # 数据隔离
        if user and hasattr(user, 'organization_id') and not user.is_superuser:
            type_query = type_query.where(AgentAlert.organization_id == user.organization_id)
        
        type_query = type_query.group_by(AgentAlert.alert_type)
        
        type_result = await self.db.execute(type_query)
        type_distribution = {row.alert_type: row.count for row in type_result}
        
        return {
            "total": total,
            "by_severity": severity_distribution,
            "by_type": type_distribution,
            "high_priority": severity_distribution.get("high", 0)
        }
    
    async def generate_daily_briefing(self, user: Any = None) -> Dict[str, Any]:
        """
        生成每日简报
        
        Args:
            user: 当前用户（用于数据隔离）
        """
        alerts = await self.get_active_alerts(limit=10, user=user)
        summary = await self.get_alert_summary(user=user)
        
        today_followups_query = select(func.count()).select_from(FollowUp).where(
            and_(
                FollowUp.next_date >= datetime.now().replace(hour=0, minute=0, second=0),
                FollowUp.next_date < datetime.now().replace(hour=23, minute=59, second=59)
            )
        )
        today_followups_result = await self.db.execute(today_followups_query)
        today_followups = today_followups_result.scalar()
        
        active_opportunities_query = select(
            func.count(),
            func.sum(Opportunity.amount)
        ).select_from(Opportunity).where(
            Opportunity.stage.notin_(["closed_won", "closed_lost"])
        )
        active_result = await self.db.execute(active_opportunities_query)
        active_row = active_result.one()
        active_opportunities = active_row[0] or 0
        pipeline_value = active_row[1] or 0
        
        briefing = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": {
                "total_alerts": summary["total"],
                "high_priority": summary["high_priority"],
                "today_followups": today_followups,
                "active_opportunities": active_opportunities,
                "pipeline_value": pipeline_value
            },
            "alerts": [
                {
                    "id": a.id,
                    "type": a.alert_type,
                    "severity": a.severity,
                    "title": a.title,
                    "entity_name": a.entity_name,
                    "suggested_action": a.suggested_action
                }
                for a in alerts
            ],
            "recommendations": []
        }
        
        if summary["high_priority"] > 0:
            briefing["recommendations"].append(
                f"有 {summary['high_priority']} 条高优先级预警需要立即处理"
            )
        
        if today_followups > 0:
            briefing["recommendations"].append(
                f"今日有 {today_followups} 个跟进任务待完成"
            )
        
        if pipeline_value > 0:
            briefing["recommendations"].append(
                f"当前销售漏斗价值 {pipeline_value/10000:.1f} 万元"
            )
        
        return briefing
