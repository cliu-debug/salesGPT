"""
执行Agent服务 - 执行具体的销售操作
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import (
    Customer, Opportunity, Quote, FollowUp,
    AgentTask, AgentMemory, AgentAlert,
    TaskStatus, TaskPriority
)
from app.services.ai_service import ai_service
from app.services.memory_service import MemoryService
from app.core.logger import logger


class ExecutionAgent:
    """
    执行Agent - 执行具体的销售操作
    
    执行能力:
    1. 创建跟进任务
    2. 更新客户状态
    3. 生成并发送报价
    4. 创建销售机会
    5. 执行批量操作
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)
    
    async def create_task(
        self,
        task_type: str,
        title: str,
        description: str = None,
        priority: str = TaskPriority.MEDIUM.value,
        target_entity_type: str = None,
        target_entity_id: int = None,
        action_plan: Dict = None,
        scheduled_at: datetime = None
    ) -> AgentTask:
        """
        创建执行任务
        """
        task = AgentTask(
            task_type=task_type,
            title=title,
            description=description,
            priority=priority,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            action_plan=action_plan or {},
            scheduled_at=scheduled_at,
            status=TaskStatus.PENDING.value
        )
        
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"创建执行任务: {task.id} - {title}")
        
        return task
    
    async def execute_task(self, task_id: int) -> Dict[str, Any]:
        """
        执行任务
        """
        query = select(AgentTask).where(AgentTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            return {"success": False, "error": "任务不存在"}
        
        if task.status == TaskStatus.COMPLETED.value:
            return {"success": False, "error": "任务已完成"}
        
        task.status = TaskStatus.IN_PROGRESS.value
        task.started_at = datetime.now()
        await self.db.commit()
        
        try:
            result = await self._execute_by_type(task)
            
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.now()
            task.result = result
            await self.db.commit()
            
            await self.memory_service.store_interaction(
                entity_type="task",
                entity_id=task.id,
                interaction_type="execution",
                content=f"执行任务: {task.title}",
                outcome="成功" if result.get("success") else "失败"
            )
            
            logger.info(f"任务执行完成: {task.id}")
            
            return {"success": True, "result": result}
            
        except Exception as e:
            task.status = TaskStatus.FAILED.value
            task.error_message = str(e)
            task.retry_count += 1
            await self.db.commit()
            
            logger.error(f"任务执行失败: {task.id} - {e}")
            
            return {"success": False, "error": str(e)}
    
    async def _execute_by_type(self, task: AgentTask) -> Dict[str, Any]:
        """
        根据任务类型执行
        """
        handlers = {
            "create_followup": self._execute_create_followup,
            "update_customer_status": self._execute_update_customer_status,
            "create_opportunity": self._execute_create_opportunity,
            "generate_quote": self._execute_generate_quote,
            "send_notification": self._execute_send_notification,
            "batch_update": self._execute_batch_update,
            "ai_analysis": self._execute_ai_analysis
        }
        
        handler = handlers.get(task.task_type)
        if not handler:
            return {"success": False, "error": f"未知任务类型: {task.task_type}"}
        
        return await handler(task)
    
    async def _execute_create_followup(self, task: AgentTask) -> Dict[str, Any]:
        """
        执行创建跟进任务
        """
        plan = task.action_plan
        customer_id = plan.get("customer_id")
        content = plan.get("content")
        next_action = plan.get("next_action")
        next_date = plan.get("next_date")
        
        if not customer_id or not content:
            return {"success": False, "error": "缺少必要参数"}
        
        customer_query = select(Customer).where(Customer.id == customer_id)
        customer_result = await self.db.execute(customer_query)
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            return {"success": False, "error": "客户不存在"}
        
        followup = FollowUp(
            customer_id=customer_id,
            customer_name=customer.name,
            content=content,
            next_action=next_action,
            next_date=datetime.fromisoformat(next_date) if next_date else None
        )
        
        self.db.add(followup)
        await self.db.commit()
        
        return {
            "success": True,
            "followup_id": followup.id,
            "message": f"已为客户 {customer.name} 创建跟进任务"
        }
    
    async def _execute_update_customer_status(self, task: AgentTask) -> Dict[str, Any]:
        """
        执行更新客户状态
        """
        plan = task.action_plan
        customer_id = plan.get("customer_id")
        new_status = plan.get("new_status")
        
        if not customer_id or not new_status:
            return {"success": False, "error": "缺少必要参数"}
        
        query = select(Customer).where(Customer.id == customer_id)
        result = await self.db.execute(query)
        customer = result.scalar_one_or_none()
        
        if not customer:
            return {"success": False, "error": "客户不存在"}
        
        old_status = customer.status
        customer.status = new_status
        await self.db.commit()
        
        return {
            "success": True,
            "customer_id": customer_id,
            "old_status": old_status,
            "new_status": new_status,
            "message": f"客户状态已从 {old_status} 更新为 {new_status}"
        }
    
    async def _execute_create_opportunity(self, task: AgentTask) -> Dict[str, Any]:
        """
        执行创建销售机会
        """
        plan = task.action_plan
        
        opportunity = Opportunity(
            name=plan.get("name"),
            customer_id=plan.get("customer_id"),
            customer_name=plan.get("customer_name"),
            amount=plan.get("amount", 0),
            stage=plan.get("stage", "initial"),
            expected_date=plan.get("expected_date"),
            remark=plan.get("remark")
        )
        
        self.db.add(opportunity)
        await self.db.commit()
        await self.db.refresh(opportunity)
        
        return {
            "success": True,
            "opportunity_id": opportunity.id,
            "message": f"销售机会「{opportunity.name}」创建成功"
        }
    
    async def _execute_generate_quote(self, task: AgentTask) -> Dict[str, Any]:
        """
        执行生成报价单
        """
        plan = task.action_plan
        
        quote = Quote(
            customer_id=plan.get("customer_id"),
            customer_name=plan.get("customer_name"),
            items=plan.get("items", []),
            total_amount=plan.get("total_amount", 0),
            status="draft",
            valid_until=plan.get("valid_until")
        )
        
        self.db.add(quote)
        await self.db.commit()
        await self.db.refresh(quote)
        
        return {
            "success": True,
            "quote_id": quote.id,
            "message": f"报价单 #{quote.id} 创建成功"
        }
    
    async def _execute_send_notification(self, task: AgentTask) -> Dict[str, Any]:
        """
        执行发送通知
        """
        plan = task.action_plan
        
        notification = {
            "type": plan.get("notification_type", "info"),
            "title": plan.get("title"),
            "content": plan.get("content"),
            "recipient": plan.get("recipient"),
            "sent_at": datetime.now().isoformat()
        }
        
        logger.info(f"发送通知: {notification}")
        
        return {
            "success": True,
            "notification": notification,
            "message": "通知已发送"
        }
    
    async def _execute_batch_update(self, task: AgentTask) -> Dict[str, Any]:
        """
        执行批量更新
        """
        plan = task.action_plan
        entity_type = plan.get("entity_type")
        entity_ids = plan.get("entity_ids", [])
        updates = plan.get("updates", {})
        
        if not entity_type or not entity_ids or not updates:
            return {"success": False, "error": "缺少必要参数"}
        
        model_map = {
            "customer": Customer,
            "opportunity": Opportunity,
            "quote": Quote,
            "followup": FollowUp
        }
        
        model = model_map.get(entity_type)
        if not model:
            return {"success": False, "error": f"未知实体类型: {entity_type}"}
        
        updated_count = 0
        for entity_id in entity_ids:
            query = select(model).where(model.id == entity_id)
            result = await self.db.execute(query)
            entity = result.scalar_one_or_none()
            
            if entity:
                for key, value in updates.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                updated_count += 1
        
        await self.db.commit()
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"已更新 {updated_count} 条记录"
        }
    
    async def _execute_ai_analysis(self, task: AgentTask) -> Dict[str, Any]:
        """
        执行AI分析
        """
        plan = task.action_plan
        analysis_type = plan.get("analysis_type")
        target_id = plan.get("target_id")
        
        from app.services.analysis_agent import AnalysisAgent
        analysis_agent = AnalysisAgent(self.db)
        
        result = {}
        
        if analysis_type == "customer_value":
            result = await analysis_agent.analyze_customer_value(target_id)
        elif analysis_type == "opportunity_risk":
            result = await analysis_agent.analyze_opportunity_risk(target_id)
        elif analysis_type == "sales_funnel":
            result = await analysis_agent.analyze_sales_funnel()
        elif analysis_type == "sales_trend":
            result = await analysis_agent.analyze_sales_trend()
        else:
            result = {"error": f"未知分析类型: {analysis_type}"}
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "result": result
        }
    
    async def schedule_followup(
        self,
        customer_id: int,
        content: str,
        next_action: str = None,
        next_date: datetime = None,
        priority: str = TaskPriority.MEDIUM.value
    ) -> AgentTask:
        """
        安排跟进任务
        """
        customer_query = select(Customer).where(Customer.id == customer_id)
        customer_result = await self.db.execute(customer_query)
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            raise ValueError("客户不存在")
        
        return await self.create_task(
            task_type="create_followup",
            title=f"跟进客户: {customer.name}",
            description=content,
            priority=priority,
            target_entity_type="customer",
            target_entity_id=customer_id,
            action_plan={
                "customer_id": customer_id,
                "content": content,
                "next_action": next_action,
                "next_date": next_date.isoformat() if next_date else None
            },
            scheduled_at=next_date
        )
    
    async def batch_create_followups(
        self,
        customer_ids: List[int],
        content_template: str,
        scheduled_date: datetime = None
    ) -> Dict[str, Any]:
        """
        批量创建跟进任务
        """
        created_tasks = []
        failed = []
        
        for customer_id in customer_ids:
            try:
                task = await self.schedule_followup(
                    customer_id=customer_id,
                    content=content_template,
                    next_date=scheduled_date
                )
                created_tasks.append(task.id)
            except Exception as e:
                failed.append({"customer_id": customer_id, "error": str(e)})
        
        return {
            "success": True,
            "created_count": len(created_tasks),
            "task_ids": created_tasks,
            "failed": failed
        }
    
    async def auto_update_stale_customers(
        self,
        days_threshold: int = 30
    ) -> Dict[str, Any]:
        """
        自动更新长期未联系的客户状态
        """
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        query = select(Customer).where(
            Customer.updated_at < cutoff_date,
            Customer.status.in_(["interested", "negotiating"])
        )
        
        result = await self.db.execute(query)
        stale_customers = result.scalars().all()
        
        updated_count = 0
        for customer in stale_customers:
            customer.status = "potential"
            customer.updated_at = datetime.now()
            updated_count += 1
        
        await self.db.commit()
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"已将 {updated_count} 个长期未联系的客户状态更新为潜在客户"
        }
    
    async def get_pending_tasks(
        self,
        limit: int = 20
    ) -> List[AgentTask]:
        """
        获取待执行任务
        """
        query = select(AgentTask).where(
            AgentTask.status == TaskStatus.PENDING.value
        ).order_by(
            AgentTask.priority.desc(),
            AgentTask.scheduled_at
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """
        获取任务统计
        """
        from sqlalchemy import func
        
        status_query = select(
            AgentTask.status,
            func.count(AgentTask.id).label('count')
        ).group_by(AgentTask.status)
        
        status_result = await self.db.execute(status_query)
        status_distribution = {row.status: row.count for row in status_result}
        
        type_query = select(
            AgentTask.task_type,
            func.count(AgentTask.id).label('count')
        ).group_by(AgentTask.task_type)
        
        type_result = await self.db.execute(type_query)
        type_distribution = {row.task_type: row.count for row in type_result}
        
        return {
            "by_status": status_distribution,
            "by_type": type_distribution,
            "total_pending": status_distribution.get(TaskStatus.PENDING.value, 0),
            "total_completed": status_distribution.get(TaskStatus.COMPLETED.value, 0),
            "total_failed": status_distribution.get(TaskStatus.FAILED.value, 0)
        }
    
    async def retry_failed_tasks(
        self,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        重试失败的任务
        """
        query = select(AgentTask).where(
            AgentTask.status == TaskStatus.FAILED.value,
            AgentTask.retry_count < max_retries
        )
        
        result = await self.db.execute(query)
        failed_tasks = result.scalars().all()
        
        retried = []
        for task in failed_tasks:
            execution_result = await self.execute_task(task.id)
            retried.append({
                "task_id": task.id,
                "success": execution_result.get("success")
            })
        
        return {
            "success": True,
            "retried_count": len(retried),
            "results": retried
        }
