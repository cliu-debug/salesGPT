from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./sales_assistant.db"
    
    # 安全配置（生产环境必须设置）
    SECRET_KEY: str = "dev-secret-key-change-in-production-please"  # 开发默认值，生产环境必须设置
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # AI服务配置
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_MODEL: str = "qwen-max"
    
    # 应用配置
    APP_NAME: str = "AI销售助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库连接池配置（PostgreSQL）
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        case_sensitive = True


settings = Settings()
