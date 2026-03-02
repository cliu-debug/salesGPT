"""
Agent任务调度器 - 定时执行Agent任务
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.logger import logger
from app.services.agent_supervisor import AgentSupervisor
from app.services.monitoring_agent import MonitoringAgent
from app.services.execution_agent import ExecutionAgent
from app.services.notification_agent import NotificationAgent
from app.services.memory_service import MemoryService


class AgentScheduler:
    """
    Agent任务调度器
    
    定时任务:
    1. 每5分钟 - 执行待处理任务
    2. 每小时 - 执行监控扫描
    3. 每天9点 - 发送今日提醒
    4. 每天18点 - 生成日报
    5. 每周一 - 生成周报
    """
    
    def __init__(self):
        self.engine = create_async_engine(settings.DATABASE_URL, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.running = False
        self.tasks = []
    
    async def start(self):
        """
        启动调度器
        """
        if self.running:
            logger.warning("调度器已在运行中")
            return
        
        self.running = True
        logger.info("Agent调度器启动...")
        
        self.tasks = [
            asyncio.create_task(self._run_pending_tasks_loop()),
            asyncio.create_task(self._run_monitoring_loop()),
            asyncio.create_task(self._run_daily_tasks()),
        ]
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
    
    async def stop(self):
        """
        停止调度器
        """
        self.running = False
        for task in self.tasks:
            task.cancel()
        logger.info("Agent调度器已停止")
    
    async def _get_session(self) -> AsyncSession:
        """
        获取数据库会话
        """
        return self.async_session()
    
    async def _run_pending_tasks_loop(self):
        """
        每5分钟执行待处理任务
        """
        while self.running:
            try:
                async with self.async_session() as db:
                    execution_agent = ExecutionAgent(db)
                    pending_tasks = await execution_agent.get_pending_tasks(limit=5)
                    
                    for task in pending_tasks:
                        if task.scheduled_at and task.scheduled_at <= datetime.now():
                            result = await execution_agent.execute_task(task.id)
                            logger.info(f"执行任务 {task.id}: {result}")
                
            except Exception as e:
                logger.error(f"执行待处理任务失败: {e}")
            
            await asyncio.sleep(300)
    
    async def _run_monitoring_loop(self):
        """
        每小时执行监控扫描
        """
        while self.running:
            try:
                async with self.async_session() as db:
                    monitoring_agent = MonitoringAgent(db)
                    alerts = await monitoring_agent.scan_all()
                    logger.info(f"监控扫描完成，发现 {len(alerts)} 条预警")
                    
                    memory_service = MemoryService(db)
                    expired = await memory_service.forget_expired()
                    if expired > 0:
                        logger.info(f"清理了 {expired} 条过期记忆")
                
            except Exception as e:
                logger.error(f"监控扫描失败: {e}")
            
            await asyncio.sleep(3600)
    
    async def _run_daily_tasks(self):
        """
        每日任务检查
        """
        while self.running:
            now = datetime.now()
            
            try:
                if now.hour == 9 and now.minute < 5:
                    await self._send_morning_reminders()
                
                if now.hour == 18 and now.minute < 5:
                    await self._generate_daily_report()
                
                if now.weekday() == 0 and now.hour == 9 and now.minute < 5:
                    await self._generate_weekly_report()
                
            except Exception as e:
                logger.error(f"每日任务执行失败: {e}")
            
            await asyncio.sleep(60)
    
    async def _send_morning_reminders(self):
        """
        发送早间提醒
        """
        async with self.async_session() as db:
            notification_agent = NotificationAgent(db)
            reminders = await notification_agent.get_today_reminders()
            
            logger.info(f"早间提醒: {reminders['summary']}")
            
            await notification_agent.batch_send_reminders("today_followups")
    
    async def _generate_daily_report(self):
        """
        生成日报
        """
        async with self.async_session() as db:
            notification_agent = NotificationAgent(db)
            report = await notification_agent.generate_daily_report()
            
            logger.info(f"日报生成完成: {report['metrics']}")
    
    async def _generate_weekly_report(self):
        """
        生成周报
        """
        async with self.async_session() as db:
            supervisor = AgentSupervisor(db)
            summary = await supervisor.generate_weekly_summary()
            
            logger.info(f"周报生成完成: {summary['sections']['weekly_report']['metrics']}")
    
    async def run_once(self, task_type: str = "all"):
        """
        手动执行一次任务
        """
        async with self.async_session() as db:
            if task_type in ["all", "monitoring"]:
                monitoring_agent = MonitoringAgent(db)
                alerts = await monitoring_agent.scan_all()
                logger.info(f"监控扫描: 发现 {len(alerts)} 条预警")
            
            if task_type in ["all", "workflow"]:
                supervisor = AgentSupervisor(db)
                result = await supervisor.run_daily_workflow()
                logger.info(f"工作流执行: {result['summary']}")
            
            if task_type in ["all", "tasks"]:
                execution_agent = ExecutionAgent(db)
                pending = await execution_agent.get_pending_tasks()
                for task in pending[:5]:
                    result = await execution_agent.execute_task(task.id)
                    logger.info(f"任务 {task.id}: {result}")


scheduler = AgentScheduler()


async def start_scheduler():
    """
    启动调度器
    """
    await scheduler.start()


async def stop_scheduler():
    """
    停止调度器
    """
    await scheduler.stop()
