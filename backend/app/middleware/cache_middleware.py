"""
缓存中间件 - 自动缓存API响应
"""
import json
import hashlib
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.services.cache_service import get_cache_service

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """
    API响应缓存中间件
    
    自动缓存GET请求的响应，减少数据库查询
    """
    
    # 可缓存的路径模式
    CACHEABLE_PATHS = [
        "/api/customers",
        "/api/opportunities",
        "/api/quotes",
        "/api/follow-ups",
        "/api/dashboard",
        "/api/analytics",
    ]
    
    # 不可缓存的路径
    NON_CACHEABLE_PATHS = [
        "/api/auth",
        "/api/ai",
        "/api/monitoring",
        "/api/io",
    ]
    
    # 各路径的缓存时间配置（秒）
    CACHE_TTL = {
        "/api/customers": 60,
        "/api/opportunities": 60,
        "/api/quotes": 60,
        "/api/follow-ups": 60,
        "/api/dashboard": 60,
        "/api/analytics": 300,
    }
    
    def __init__(self, app, cache_service=None):
        super().__init__(app)
        self.cache_service = cache_service
    
    def _should_cache(self, request: Request) -> bool:
        """判断请求是否应该缓存"""
        # 只缓存GET请求
        if request.method != "GET":
            return False
        
        path = request.url.path
        
        # 检查是否在排除列表中
        for non_cacheable in self.NON_CACHEABLE_PATHS:
            if path.startswith(non_cacheable):
                return False
        
        # 检查是否在可缓存列表中
        for cacheable in self.CACHEABLE_PATHS:
            if path.startswith(cacheable):
                return True
        
        return False
    
    def _generate_cache_key(self, request: Request) -> str:
        """生成缓存键"""
        # 基于路径、查询参数和用户ID生成键
        path = request.url.path
        query = str(request.query_params)
        
        # 从请求头获取用户信息（如果有）
        user_id = request.headers.get("X-User-ID", "anonymous")
        
        content = f"{path}:{query}:{user_id}"
        hash_key = hashlib.md5(content.encode()).hexdigest()[:16]
        
        return f"api_response:{hash_key}"
    
    def _get_ttl(self, request: Request) -> int:
        """获取缓存时间"""
        path = request.url.path
        
        for prefix, ttl in self.CACHE_TTL.items():
            if path.startswith(prefix):
                return ttl
        
        return 60  # 默认1分钟
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 检查是否应该缓存
        if not self._should_cache(request):
            return await call_next(request)
        
        # 获取缓存服务
        cache = self.cache_service or get_cache_service()
        
        # 生成缓存键
        cache_key = self._generate_cache_key(request)
        
        # 尝试从缓存获取
        cached_response = await cache.get("api", key=cache_key)
        if cached_response:
            logger.debug(f"API缓存命中: {request.url.path}")
            return JSONResponse(
                content=cached_response["body"],
                status_code=cached_response["status_code"],
                headers={"X-Cache": "HIT"}
            )
        
        # 执行请求
        response = await call_next(request)
        
        # 缓存成功的响应
        if response.status_code == 200:
            try:
                # 读取响应体
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # 解析JSON
                body_json = json.loads(response_body.decode())
                
                # 缓存
                ttl = self._get_ttl(request)
                await cache.set(
                    "api",
                    {
                        "body": body_json,
                        "status_code": response.status_code
                    },
                    ttl=ttl,
                    key=cache_key
                )
                
                logger.debug(f"API响应已缓存: {request.url.path}, TTL={ttl}秒")
                
                # 返回响应
                return JSONResponse(
                    content=body_json,
                    status_code=response.status_code,
                    headers={**response.headers, "X-Cache": "MISS"}
                )
            
            except Exception as e:
                logger.warning(f"缓存响应失败: {e}")
                return response
        
        return response


def invalidate_cache(namespace: str):
    """
    缓存失效装饰器
    
    在操作完成后清除相关缓存
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # 清除缓存
            cache = get_cache_service()
            await cache.clear_namespace(namespace)
            logger.debug(f"已清除缓存: {namespace}")
            
            return result
        return wrapper
    return decorator
