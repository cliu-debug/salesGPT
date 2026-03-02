from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import auth, customer, opportunity, quote, followup, dashboard, ai, import_export, analytics, agent, monitoring
from app.core.database import init_db, close_db
from app.core.config import settings
from app.core.logger import logger
from app.middleware.performance import PerformanceMiddleware, RequestIDMiddleware

app = FastAPI(
    title="AI销售助手",
    description="智能销售管理系统API - 让一个人也能像团队一样高效卖货",
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# 添加中间件（注意顺序：最后添加的最先执行）
app.add_middleware(PerformanceMiddleware)
app.add_middleware(RequestIDMiddleware)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误",
            "error": str(exc) if app.debug else "Internal Server Error"
        }
    )


app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(customer.router, prefix="/api/customers", tags=["客户管理"])
app.include_router(opportunity.router, prefix="/api/opportunities", tags=["销售机会"])
app.include_router(quote.router, prefix="/api/quotes", tags=["报价管理"])
app.include_router(followup.router, prefix="/api/follow-ups", tags=["跟进管理"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI助手"])
app.include_router(import_export.router, prefix="/api/import-export", tags=["导入导出"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["数据分析"])
app.include_router(agent.router, prefix="/api/agent", tags=["智能体"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["监控"])


@app.on_event("startup")
async def startup():
    """应用启动事件"""
    logger.info("=" * 60)
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    
    # 初始化数据库
    await init_db()
    
    logger.info("✅ 应用启动完成")


@app.on_event("shutdown")
async def shutdown():
    """应用关闭事件"""
    logger.info("正在关闭应用...")
    
    # 关闭数据库连接池
    await close_db()
    
    logger.info("✅ 应用已关闭")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"{settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME
    }
