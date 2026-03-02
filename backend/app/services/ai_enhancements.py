"""
AI服务增强模块 - 提供重试、降级、缓存和监控功能
"""
import hashlib
import json
import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class AIFallbackStrategy(ABC):
    """AI降级策略抽象基类"""
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """执行降级策略"""
        pass


class CustomerAnalysisFallback(AIFallbackStrategy):
    """客户分析降级策略"""
    
    async def execute(self, customer_info: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        """基于规则的客户分析"""
        logger.info("使用规则引擎降级分析客户")
        
        # 根据行业和状态推断
        industry = customer_info.get('industry', '').lower()
        status = customer_info.get('status', '').lower()
        company = customer_info.get('company', '')
        
        # 简单规则：根据公司名称长度判断客户规模
        is_big_customer = len(company) > 10 or any(
            keyword in company 
            for keyword in ['集团', '公司', '有限', '科技', '技术']
        )
        
        # 根据状态判断预算等级
        budget_map = {
            'negotiating': '高',
            'interested': '中',
            'potential': '低',
        }
        budget_level = budget_map.get(status, '中')
        
        return {
            "customer_type": "大客户" if is_big_customer else "中小客户",
            "budget_level": budget_level,
            "decision_speed": "中",
            "focus_points": ["价格", "质量", "服务"],
            "recommended_strategy": f"针对{industry}行业的客户，重点介绍产品优势和成功案例",
            "risk_assessment": "需要进一步了解客户需求和预算",
            "next_steps": ["安排产品演示", "提供报价方案"],
            "_fallback": True  # 标记为降级结果
        }


class QuoteSuggestionFallback(AIFallbackStrategy):
    """报价建议降级策略"""
    
    async def execute(self, customer_info: Dict[str, Any], product_info: List[Dict], *args, **kwargs) -> Dict[str, Any]:
        """基于规则的报价建议"""
        logger.info("使用规则引擎降级生成报价建议")
        
        # 计算产品总价值
        total_value = sum(
            item.get('quantity', 1) * item.get('unit_price', 0)
            for item in product_info
        )
        
        # 根据总额推荐折扣
        if total_value > 100000:
            discount = 0.85
            strategy = "高额订单建议给予15%折扣"
        elif total_value > 50000:
            discount = 0.90
            strategy = "中等订单建议给予10%折扣"
        else:
            discount = 0.95
            strategy = "小订单建议给予5%折扣"
        
        return {
            "suggestion": f"建议报价策略：{strategy}",
            "recommended_discount": f"{int((1-discount)*100)}%",
            "strategy": strategy,
            "win_probability": 0.6,
            "_fallback": True
        }


class FollowUpScriptFallback(AIFallbackStrategy):
    """跟进话术降级策略"""
    
    async def execute(self, customer_info: Dict[str, Any], *args, **kwargs) -> str:
        """基于模板的跟进话术"""
        logger.info("使用模板降级生成跟进话术")
        
        name = customer_info.get('name', '客户')
        company = customer_info.get('company', '贵司')
        status = customer_info.get('status', '潜在')
        
        return f"""
您好，{name}！

我是XX公司的销售顾问，感谢您对我们产品的关注。

针对{company}的需求，我想向您介绍我们的最新产品方案：

1. 产品核心优势介绍
2. 成功案例分享
3. 定制化解决方案

期待与您进一步沟通，请问您方便安排一个电话会议吗？

祝好！
（本话术由系统自动生成）
"""


class ProbabilityFallback(AIFallbackStrategy):
    """成交概率预测降级策略"""
    
    async def execute(self, opportunity_info: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        """基于阶段的成交概率预测"""
        logger.info("使用规则引擎降级预测成交概率")
        
        stage = opportunity_info.get('stage', 'initial')
        amount = opportunity_info.get('amount', 0)
        
        # 根据阶段预测概率
        stage_probability = {
            'initial': 0.2,
            'need_confirm': 0.3,
            'quoting': 0.5,
            'negotiating': 0.7,
            'closed_won': 1.0,
            'closed_lost': 0.0
        }
        
        base_prob = stage_probability.get(stage, 0.5)
        
        # 根据金额调整（大单风险更高）
        if amount > 500000:
            prob = base_prob * 0.9
        elif amount > 100000:
            prob = base_prob * 0.95
        else:
            prob = base_prob
        
        return {
            "probability": round(prob, 2),
            "confidence": "中",
            "key_factors": ["销售阶段", "订单金额"],
            "risks": ["竞争对手", "预算审批"],
            "suggestions": ["加强客户关系", "提供更多价值证明"],
            "next_actions": ["安排高层会面", "提供试用方案"],
            "_fallback": True
        }


class AICacheManager:
    """AI响应缓存管理器"""
    
    def __init__(self, redis_client=None, default_ttl: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            redis_client: Redis客户端实例
            default_ttl: 默认缓存时间（秒）
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self._local_cache: Dict[str, tuple] = {}  # 本地缓存后备
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 将参数序列化为字符串
        content = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, ensure_ascii=False)
        # 生成哈希
        hash_key = hashlib.md5(content.encode()).hexdigest()
        return f"ai_cache:{prefix}:{hash_key}"
    
    async def get(self, prefix: str, *args, **kwargs) -> Optional[Any]:
        """获取缓存"""
        key = self._generate_cache_key(prefix, *args, **kwargs)
        
        # 尝试从Redis获取
        if self.redis:
            try:
                cached = await self.redis.get(key)
                if cached:
                    logger.debug(f"从Redis缓存命中: {key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis读取失败: {e}")
        
        # 尝试从本地缓存获取
        if key in self._local_cache:
            cached_data, expire_time = self._local_cache[key]
            if datetime.now() < expire_time:
                logger.debug(f"从本地缓存命中: {key}")
                return cached_data
            else:
                # 过期，删除
                del self._local_cache[key]
        
        return None
    
    async def set(self, prefix: str, value: Any, ttl: Optional[int] = None, *args, **kwargs):
        """设置缓存"""
        key = self._generate_cache_key(prefix, *args, **kwargs)
        ttl = ttl or self.default_ttl
        
        # 设置Redis缓存
        if self.redis:
            try:
                await self.redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
                logger.debug(f"已设置Redis缓存: {key}, TTL={ttl}秒")
            except Exception as e:
                logger.warning(f"Redis写入失败: {e}")
        
        # 同时设置本地缓存作为后备
        expire_time = datetime.now() + timedelta(seconds=ttl)
        self._local_cache[key] = (value, expire_time)
    
    async def clear_prefix(self, prefix: str):
        """清除指定前缀的所有缓存"""
        if self.redis:
            try:
                keys = await self.redis.keys(f"ai_cache:{prefix}:*")
                if keys:
                    await self.redis.delete(*keys)
                    logger.info(f"已清除 {len(keys)} 个缓存键")
            except Exception as e:
                logger.warning(f"清除缓存失败: {e}")
        
        # 清除本地缓存
        keys_to_delete = [k for k in self._local_cache if k.startswith(f"ai_cache:{prefix}:")]
        for key in keys_to_delete:
            del self._local_cache[key]


class TokenMonitor:
    """Token使用监控器"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._usage_stats: Dict[str, List[Dict]] = {}
    
    async def record_usage(self, 
                          user_id: int,
                          model: str,
                          prompt_tokens: int,
                          completion_tokens: int,
                          total_tokens: int,
                          duration_ms: float):
        """记录Token使用情况"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "duration_ms": duration_ms
        }
        
        # 本地记录
        if user_id not in self._usage_stats:
            self._usage_stats[user_id] = []
        self._usage_stats[user_id].append(record)
        
        # Redis记录（用于持久化和跨进程共享）
        if self.redis:
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                key = f"token_usage:{user_id}:{today}"
                
                # 增加今日使用量
                await self.redis.hincrby(key, "total_tokens", total_tokens)
                await self.redis.hincrby(key, "call_count", 1)
                await self.redis.expire(key, 86400 * 30)  # 保留30天
                
                logger.debug(f"已记录Token使用: user={user_id}, tokens={total_tokens}")
            except Exception as e:
                logger.warning(f"记录Token使用失败: {e}")
    
    async def get_usage_stats(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """获取Token使用统计"""
        stats = {
            "total_tokens": 0,
            "total_calls": 0,
            "daily_usage": []
        }
        
        if self.redis:
            try:
                for i in range(days):
                    date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                    key = f"token_usage:{user_id}:{date}"
                    
                    daily_data = await self.redis.hgetall(key)
                    if daily_data:
                        stats["daily_usage"].append({
                            "date": date,
                            "tokens": int(daily_data.get("total_tokens", 0)),
                            "calls": int(daily_data.get("call_count", 0))
                        })
                        stats["total_tokens"] += int(daily_data.get("total_tokens", 0))
                        stats["total_calls"] += int(daily_data.get("call_count", 0))
            except Exception as e:
                logger.warning(f"获取Token统计失败: {e}")
        
        return stats
    
    async def check_quota(self, user_id: int, daily_limit: int = 100000) -> bool:
        """检查Token配额是否超限"""
        if self.redis:
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                key = f"token_usage:{user_id}:{today}"
                daily_usage = await self.redis.hget(key, "total_tokens")
                
                if daily_usage and int(daily_usage) >= daily_limit:
                    logger.warning(f"用户 {user_id} 已超出今日Token配额")
                    return False
            except Exception as e:
                logger.warning(f"检查Token配额失败: {e}")
        
        return True
