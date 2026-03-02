"""
SQLite 到 PostgreSQL 数据迁移脚本

使用方法：
1. 确保 PostgreSQL 数据库已创建并配置好
2. 设置环境变量 DATABASE_URL (PostgreSQL) 和 SQLITE_DATABASE_URL (SQLite)
3. 运行: python scripts/migrate_sqlite_to_postgres.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataMigrator:
    """数据迁移器"""
    
    def __init__(self, sqlite_url: str, postgres_url: str):
        self.sqlite_url = sqlite_url
        self.postgres_url = postgres_url
        
        # 创建引擎
        self.sqlite_engine = create_async_engine(sqlite_url, echo=False)
        self.postgres_engine = create_async_engine(postgres_url, echo=False)
        
        # 创建会话工厂
        self.sqlite_session = async_sessionmaker(
            self.sqlite_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.postgres_session = async_sessionmaker(
            self.postgres_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def migrate_all(self):
        """迁移所有数据"""
        logger.info("开始数据迁移...")
        
        try:
            # 导入所有模型
            from app.models.models import (
                Customer, Opportunity, Quote, FollowUp,
                AgentMemory, AgentTask, AgentAlert, AgentGoal, AgentConversation
            )
            
            # 定义迁移顺序（考虑外键依赖）
            models_to_migrate = [
                ("客户", Customer),
                ("销售机会", Opportunity),
                ("报价单", Quote),
                ("跟进记录", FollowUp),
                ("智能体记忆", AgentMemory),
                ("智能体任务", AgentTask),
                ("智能体预警", AgentAlert),
                ("智能体目标", AgentGoal),
                ("智能体对话", AgentConversation),
            ]
            
            # 迁移每个模型的数据
            for name, model in models_to_migrate:
                await self.migrate_model(name, model)
            
            logger.info("✅ 数据迁移完成！")
            
            # 打印统计信息
            await self.print_summary()
            
        except Exception as e:
            logger.error(f"❌ 数据迁移失败: {e}", exc_info=True)
            raise
        finally:
            # 清理资源
            await self.sqlite_engine.dispose()
            await self.postgres_engine.dispose()
    
    async def migrate_model(self, name: str, model):
        """迁移单个模型的数据"""
        logger.info(f"正在迁移 {name}...")
        
        async with self.sqlite_session() as sqlite_db:
            # 从SQLite读取数据
            query = select(model)
            result = await sqlite_db.execute(query)
            records = result.scalars().all()
            
            if not records:
                logger.info(f"  {name}: 没有数据需要迁移")
                return
            
            logger.info(f"  {name}: 找到 {len(records)} 条记录")
            
            # 转换为字典列表
            data_list = []
            for record in records:
                data = {}
                for column in model.__table__.columns:
                    value = getattr(record, column.name)
                    # 处理特殊类型
                    if value is not None:
                        data[column.name] = value
                data_list.append(data)
        
        # 批量插入到PostgreSQL
        async with self.postgres_session() as postgres_db:
            try:
                for data in data_list:
                    # 创建新记录
                    new_record = model(**data)
                    postgres_db.add(new_record)
                
                await postgres_db.commit()
                logger.info(f"  ✅ {name}: 成功迁移 {len(data_list)} 条记录")
                
            except Exception as e:
                await postgres_db.rollback()
                logger.error(f"  ❌ {name}: 迁移失败 - {e}")
                raise
    
    async def print_summary(self):
        """打印迁移统计信息"""
        logger.info("\n=== 迁移统计 ===")
        
        from app.models.models import (
            Customer, Opportunity, Quote, FollowUp,
            AgentMemory, AgentTask, AgentAlert, AgentGoal, AgentConversation
        )
        
        async with self.postgres_session() as db:
            models = [
                ("客户", Customer),
                ("销售机会", Opportunity),
                ("报价单", Quote),
                ("跟进记录", FollowUp),
                ("智能体记忆", AgentMemory),
                ("智能体任务", AgentTask),
                ("智能体预警", AgentAlert),
                ("智能体目标", AgentGoal),
                ("智能体对话", AgentConversation),
            ]
            
            for name, model in models:
                count_query = select(model)
                result = await db.execute(count_query)
                count = len(result.scalars().all())
                logger.info(f"{name}: {count} 条记录")


async def main():
    """主函数"""
    # 从环境变量读取配置
    sqlite_url = os.getenv("SQLITE_DATABASE_URL", "sqlite+aiosqlite:///./sales_assistant.db")
    postgres_url = os.getenv("DATABASE_URL")
    
    if not postgres_url:
        logger.error("❌ 错误: 未设置 DATABASE_URL 环境变量")
        logger.info("请设置 PostgreSQL 数据库URL，例如:")
        logger.info("export DATABASE_URL='postgresql+asyncpg://user:password@localhost/dbname'")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("SQLite → PostgreSQL 数据迁移工具")
    logger.info("=" * 60)
    logger.info(f"源数据库 (SQLite): {sqlite_url}")
    logger.info(f"目标数据库 (PostgreSQL): {postgres_url}")
    logger.info("=" * 60)
    
    # 确认迁移
    confirm = input("\n是否继续迁移? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        logger.info("已取消迁移")
        sys.exit(0)
    
    # 执行迁移
    migrator = DataMigrator(sqlite_url, postgres_url)
    await migrator.migrate_all()


if __name__ == "__main__":
    asyncio.run(main())
