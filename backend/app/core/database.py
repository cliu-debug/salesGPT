from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL

# 根据数据库类型创建引擎
if DATABASE_URL.startswith("sqlite"):
    # SQLite 配置
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DEBUG,
        future=True
    )
    logger.info("使用 SQLite 数据库")
else:
    # PostgreSQL 配置
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_recycle=3600,  # 1小时回收连接
        future=True
    )
    logger.info(f"使用 PostgreSQL 数据库，连接池大小: {settings.DB_POOL_SIZE}")

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_db():
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


async def close_db():
    """关闭数据库连接池"""
    await engine.dispose()
    logger.info("数据库连接池已关闭")
