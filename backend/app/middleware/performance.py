"""
性能监控中间件 - 收集请求性能指标
"""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import logger
from typing import Dict, List
from collections import defaultdict
import asyncio


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.request_times: Dict[str, List[float]] = defaultdict(list)
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.max_samples = 1000  # 每个端点最多保存的样本数
    
    def record_request(self, endpoint: str, duration: float, status_code: int):
        """记录请求"""
        self.request_counts[endpoint] += 1
        
        # 只保存最近的样本
        if len(self.request_times[endpoint]) >= self.max_samples:
            self.request_times[endpoint].pop(0)
        self.request_times[endpoint].append(duration)
        
        # 记录错误
        if status_code >= 400:
            self.error_counts[endpoint] += 1
    
    def get_stats(self, endpoint: str = None) -> Dict:
        """获取统计信息"""
        if endpoint:
            times = self.request_times.get(endpoint, [])
            if not times:
                return {}
            
            sorted_times = sorted(times)
            return {
                "endpoint": endpoint,
                "count": self.request_counts.get(endpoint, 0),
                "errors": self.error_counts.get(endpoint, 0),
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "p50": sorted_times[len(sorted_times) // 2],
                "p95": sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 1 else sorted_times[0],
                "p99": sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 1 else sorted_times[0],
            }
        
        # 返回所有端点的统计
        all_stats = {}
        for ep in self.request_counts.keys():
            all_stats[ep] = self.get_stats(ep)
        return all_stats
    
    def reset(self):
        """重置统计"""
        self.request_times.clear()
        self.request_counts.clear()
        self.error_counts.clear()


# 全局监控实例
performance_monitor = PerformanceMonitor()


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    性能监控中间件
    
    自动记录每个请求的响应时间和状态码
    """
    
    async def dispatch(self, request: Request, call_next):
        # 记录开始时间
        start_time = time.time()
        
        # 执行请求
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"请求处理异常: {e}", exc_info=True)
            status_code = 500
            raise
        finally:
            # 计算耗时
            duration = time.time() - start_time
            
            # 记录性能数据
            endpoint = f"{request.method} {request.url.path}"
            performance_monitor.record_request(endpoint, duration, status_code)
            
            # 记录日志（慢请求）
            if duration > 1.0:  # 超过1秒的请求
                logger.warning(
                    f"慢请求: {endpoint} - {duration:.2f}s - {status_code}"
                )
            else:
                logger.info(
                    f"请求: {endpoint} - {duration:.3f}s - {status_code}"
                )
        
        # 添加性能头
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    请求ID中间件
    
    为每个请求分配唯一ID，便于追踪
    """
    
    async def dispatch(self, request: Request, call_next):
        import uuid
        
        # 生成或获取请求ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # 设置到request.state中，便于后续使用
        request.state.request_id = request_id
        
        # 执行请求
        response = await call_next(request)
        
        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id
        
        return response
