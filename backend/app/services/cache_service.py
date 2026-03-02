"""
缓存服务模块 - 提供多层缓存策略
支持Redis分布式缓存 + 本地内存缓存
"""
import json
import hashlib
import asyncio
from typing import Optional, Any, Dict, List, Callable
from datetime import datetime, timedelta
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """
    统一缓存服务
    实现二级缓存架构：L1本地缓存 + L2 Redis缓存
    """
    
    def __init__(self, redis_client=None, default_ttl: int = 300):
        """
        初始化缓存服务
        
        Args:
            redis_client: Redis客户端实例
            default_ttl: 默认缓存时间（秒），默认5分钟
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        
        # 本地缓存存储
        self._local_cache: Dict[str, Dict] = {}
        self._local_cache_max_size = 1000  # 最大缓存条目数
        
        # 缓存统计
        self._stats = {
            "hits": 0,
            "misses": 0,
            "local_hits": 0,
            "redis_hits": 0
        }
    
    def _generate_key(self, namespace: str, *args, **kwargs) -> str:
        """生成缓存键"""
        content = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, ensure_ascii=False)
        hash_key = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"cache:{namespace}:{hash_key}"
    
    async def get(self, namespace: str, *args, **kwargs) -> Optional[Any]:
        """
        获取缓存（二级查找）
        
        查找顺序：L1本地缓存 -> L2 Redis缓存
        """
        key = self._generate_key(namespace, *args, **kwargs)
        
        # L1: 本地缓存
        if key in self._local_cache:
            entry = self._local_cache[key]
            if datetime.now() < entry["expire_at"]:
                self._stats["hits"] += 1
                self._stats["local_hits"] += 1
                logger.debug(f"本地缓存命中: {key}")
                return entry["value"]
            else:
                # 过期，删除
                del self._local_cache[key]
        
        # L2: Redis缓存
        if self.redis:
            try:
                cached = await self.redis.get(key)
                if cached:
                    value = json.loads(cached)
                    # 回填本地缓存
                    self._set_local(key, value, ttl=60)  # 本地缓存短一些
                    self._stats["hits"] += 1
                    self._stats["redis_hits"] += 1
                    logger.debug(f"Redis缓存命中: {key}")
                    return value
            except Exception as e:
                logger.warning(f"Redis读取失败: {e}")
        
        self._stats["misses"] += 1
        return None
    
    async def set(self, namespace: str, value: Any, ttl: Optional[int] = None, *args, **kwargs):
        """设置缓存（同时设置二级缓存）"""
        key = self._generate_key(namespace, *args, **kwargs)
        ttl = ttl or self.default_ttl
        
        # L2: Redis缓存
        if self.redis:
            try:
                await self.redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
                logger.debug(f"设置Redis缓存: {key}, TTL={ttl}秒")
            except Exception as e:
                logger.warning(f"Redis写入失败: {e}")
        
        # L1: 本地缓存（较短TTL）
        self._set_local(key, value, ttl=min(ttl, 300))
    
    def _set_local(self, key: str, value: Any, ttl: int):
        """设置本地缓存"""
        # LRU淘汰策略
        if len(self._local_cache) >= self._local_cache_max_size:
            # 删除最旧的条目
            oldest_key = min(
                self._local_cache.keys(),
                key=lambda k: self._local_cache[k]["created_at"]
            )
            del self._local_cache[oldest_key]
        
        self._local_cache[key] = {
            "value": value,
            "expire_at": datetime.now() + timedelta(seconds=ttl),
            "created_at": datetime.now()
        }
    
    async def delete(self, namespace: str, *args, **kwargs):
        """删除缓存"""
        key = self._generate_key(namespace, *args, **kwargs)
        
        # 删除本地缓存
        if key in self._local_cache:
            del self._local_cache[key]
        
        # 删除Redis缓存
        if self.redis:
            try:
                await self.redis.delete(key)
                logger.debug(f"删除缓存: {key}")
            except Exception as e:
                logger.warning(f"Redis删除失败: {e}")
    
    async def clear_namespace(self, namespace: str):
        """清除指定命名空间的所有缓存"""
        # 清除本地缓存
        prefix = f"cache:{namespace}:"
        keys_to_delete = [k for k in self._local_cache if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._local_cache[key]
        
        # 清除Redis缓存
        if self.redis:
            try:
                keys = await self.redis.keys(f"{prefix}*")
                if keys:
                    await self.redis.delete(*keys)
                    logger.info(f"清除命名空间缓存: {namespace}, {len(keys)}条")
            except Exception as e:
                logger.warning(f"清除Redis缓存失败: {e}")
    
    async def get_or_set(
        self,
        namespace: str,
        factory: Callable,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        获取缓存，如果不存在则调用factory生成并缓存
        
        Args:
            namespace: 缓存命名空间
            factory: 异步生成函数
            ttl: 缓存时间
        """
        value = await self.get(namespace, *args, **kwargs)
        if value is not None:
            return value
        
        # 生成新值
        if asyncio.iscoroutinefunction(factory):
            value = await factory(*args, **kwargs)
        else:
            value = factory(*args, **kwargs)
        
        # 缓存
        await self.set(namespace, value, ttl, *args, **kwargs)
        return value
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total * 100 if total > 0 else 0
        
        return {
            **self._stats,
            "total_requests": total,
            "hit_rate": f"{hit_rate:.2f}%",
            "local_cache_size": len(self._local_cache)
        }
    
    def clear_stats(self):
        """清除统计"""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "local_hits": 0,
            "redis_hits": 0
        }


def cached(namespace: str, ttl: int = 300):
    """
    缓存装饰器
    
    用法:
        @cached("customer_list", ttl=60)
        async def get_customers(org_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(cache_service: CacheService, *args, **kwargs):
            # 提取缓存相关参数
            cache_key_args = {k: v for k, v in kwargs.items() if not k.startswith('_')}
            
            # 尝试从缓存获取
            result = await cache_service.get(namespace, *args, **cache_key_args)
            if result is not None:
                return result
            
            # 调用原函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            await cache_service.set(namespace, result, ttl, *args, **cache_key_args)
            
            return result
        return wrapper
    return decorator


# 预定义缓存配置
CACHE_CONFIGS = {
    # 客户相关缓存
    "customer_list": {"ttl": 60, "namespace": "customers"},      # 客户列表缓存1分钟
    "customer_detail": {"ttl": 300, "namespace": "customer"},    # 客户详情缓存5分钟
    "customer_stats": {"ttl": 300, "namespace": "customer_stats"}, # 客户统计缓存5分钟
    
    # 机会相关缓存
    "opportunity_list": {"ttl": 60, "namespace": "opportunities"},
    "opportunity_detail": {"ttl": 300, "namespace": "opportunity"},
    "funnel_stats": {"ttl": 300, "namespace": "funnel"},
    
    # 报价相关缓存
    "quote_list": {"ttl": 60, "namespace": "quotes"},
    "quote_detail": {"ttl": 300, "namespace": "quote"},
    
    # 仪表盘缓存
    "dashboard": {"ttl": 60, "namespace": "dashboard"},
    
    # AI响应缓存
    "ai_response": {"ttl": 3600, "namespace": "ai"},  # AI响应缓存1小时
    
    # 用户权限缓存
    "user_permissions": {"ttl": 1800, "namespace": "permissions"},  # 权限缓存30分钟
}


# 全局缓存服务实例
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取全局缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        # 延迟初始化，避免循环导入
        _cache_service = CacheService()
    return _cache_service


def init_cache_service(redis_client=None, default_ttl: int = 300):
    """初始化全局缓存服务"""
    global _cache_service
    _cache_service = CacheService(redis_client=redis_client, default_ttl=default_ttl)
    logger.info("缓存服务初始化完成")
    return _cache_service
