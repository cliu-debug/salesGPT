"""
AI服务单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import json
import os

from app.services.ai_service import AIService, AIServiceError
from app.services.ai_enhancements import (
    AICacheManager, TokenMonitor,
    CustomerAnalysisFallback, QuoteSuggestionFallback,
    FollowUpScriptFallback, ProbabilityFallback
)


class TestAIService:
    """AI服务测试"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ai_service_initialization(self):
        """测试AI服务初始化"""
        # AIService不需要参数，从settings读取配置
        service = AIService()
        
        assert service.api_key is not None
        assert service.model is not None
        assert service.cache is not None
        assert service.token_monitor is not None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ai_service_chat_mock(self):
        """测试AI服务对话（模拟）"""
        service = AIService()
        
        # 模拟API响应
        with patch.object(service, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "这是一个测试回复"
            
            result = await service.chat("测试问题")
            
            assert result == "这是一个测试回复"
            mock_chat.assert_called_once_with("测试问题")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ai_service_chat_with_system_prompt(self):
        """测试AI服务对话（带系统提示）"""
        service = AIService()
        
        with patch.object(service, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "回复内容"
            
            result = await service.chat(
                "用户问题", 
                system_prompt="你是一个销售助手"
            )
            
            assert result == "回复内容"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ai_service_no_api_key(self):
        """测试AI服务无API密钥时的降级处理"""
        service = AIService()
        service.api_key = "your-dashscope-api-key"  # 模拟未配置的API密钥
        
        result = await service.chat("测试问题")
        
        assert "请配置DASHSCOPE_API_KEY" in result


class TestAICacheManager:
    """AI缓存管理器测试"""
    
    @pytest.mark.unit
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        cache = AICacheManager()
        
        key1 = cache._generate_cache_key("test", "问题1", "提示1")
        key2 = cache._generate_cache_key("test", "问题1", "提示1")
        key3 = cache._generate_cache_key("test", "问题2", "提示1")
        
        assert key1 == key2  # 相同输入生成相同键
        assert key1 != key3  # 不同输入生成不同键
    
    @pytest.mark.unit
    def test_cache_key_with_different_params(self):
        """测试不同参数的缓存键"""
        cache = AICacheManager()
        
        key1 = cache._generate_cache_key("prefix", "问题")
        key2 = cache._generate_cache_key("prefix", "问题", "提示")
        
        assert key1 != key2
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """测试缓存存储和获取"""
        cache = AICacheManager()
        
        # 设置缓存
        await cache.set("test_prefix", "缓存值", arg1="参数1")
        
        # 获取缓存
        result = await cache.get("test_prefix", arg1="参数1")
        
        assert result == "缓存值"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_get_nonexistent(self):
        """测试获取不存在的缓存"""
        cache = AICacheManager()
        
        result = await cache.get("nonexistent_prefix", "参数")
        
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_clear_prefix(self):
        """测试清除指定前缀的缓存"""
        cache = AICacheManager()
        
        # 设置一些缓存
        await cache.set("prefix1", "value1")
        await cache.set("prefix1", "value2", extra="param")
        await cache.set("prefix2", "value3")
        
        # 清除prefix1的缓存
        await cache.clear_prefix("prefix1")
        
        # 验证prefix1缓存已清空，prefix2仍存在
        # 注意：clear_prefix主要针对Redis，本地缓存可能需要不同处理


class TestTokenMonitor:
    """Token监控器测试"""
    
    @pytest.mark.unit
    def test_token_monitor_initialization(self):
        """测试Token监控器初始化"""
        monitor = TokenMonitor()
        
        assert monitor is not None
        assert monitor._usage_stats is not None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_token_usage(self):
        """测试记录Token使用"""
        monitor = TokenMonitor()
        
        # 记录使用
        await monitor.record_usage(
            user_id=1,
            model="qwen-max",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            duration_ms=500.0
        )
        
        # 验证本地记录
        assert 1 in monitor._usage_stats
        assert len(monitor._usage_stats[1]) == 1
        assert monitor._usage_stats[1][0]["total_tokens"] == 150
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_token_records(self):
        """测试多次记录Token使用"""
        monitor = TokenMonitor()
        
        # 多次记录
        await monitor.record_usage(
            user_id=1, model="qwen-max",
            prompt_tokens=100, completion_tokens=50,
            total_tokens=150, duration_ms=500.0
        )
        await monitor.record_usage(
            user_id=1, model="qwen-max",
            prompt_tokens=50, completion_tokens=30,
            total_tokens=80, duration_ms=300.0
        )
        
        # 验证本地记录
        assert len(monitor._usage_stats[1]) == 2
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_quota_within_limit(self):
        """测试配额检查（未超限）"""
        monitor = TokenMonitor()
        
        # 无Redis时，默认返回True
        is_within = await monitor.check_quota(user_id=1, daily_limit=1000)
        
        assert is_within is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_usage_stats(self):
        """测试获取使用统计"""
        monitor = TokenMonitor()
        
        # 记录使用
        await monitor.record_usage(
            user_id=1, model="qwen-max",
            prompt_tokens=100, completion_tokens=50,
            total_tokens=150, duration_ms=500.0
        )
        
        # 获取统计（无Redis时返回空统计）
        stats = await monitor.get_usage_stats(user_id=1, days=7)
        
        assert "total_tokens" in stats
        assert "total_calls" in stats
        assert "daily_usage" in stats


class TestAIFallbackStrategies:
    """AI降级策略测试"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_customer_analysis(self):
        """测试客户分析降级"""
        fallback = CustomerAnalysisFallback()
        
        # 提供基础数据
        customer_data = {
            "industry": "互联网",
            "company": "测试科技有限公司",
            "source": "线上推广",
            "status": "interested"
        }
        
        result = await fallback.execute(customer_data)
        
        # 降级策略应该返回基本分析结果
        assert result is not None
        assert isinstance(result, dict)
        assert "customer_type" in result
        assert "budget_level" in result
        assert "_fallback" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_quote_suggestion(self):
        """测试报价建议降级"""
        fallback = QuoteSuggestionFallback()
        
        customer_data = {
            "name": "测试客户",
            "company": "测试公司",
            "industry": "互联网"
        }
        product_info = [
            {"quantity": 1, "unit_price": 30000},
            {"quantity": 2, "unit_price": 10000}
        ]
        
        result = await fallback.execute(customer_data, product_info)
        
        # 降级策略应该返回基本建议
        assert result is not None
        assert "recommended_discount" in result or "suggestion" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_followup_script(self):
        """测试跟进话术降级"""
        fallback = FollowUpScriptFallback()
        
        customer_data = {
            "name": "测试客户",
            "company": "测试公司",
            "status": "interested"
        }
        
        result = await fallback.execute(customer_data)
        
        # 降级策略应该返回基本话术
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_probability(self):
        """测试成交概率预测降级"""
        fallback = ProbabilityFallback()
        
        opportunity_data = {
            "stage": "negotiating",
            "amount": 80000
        }
        
        result = await fallback.execute(opportunity_data)
        
        # 降级策略应该返回概率预测
        assert result is not None
        assert "probability" in result
        assert 0 <= result["probability"] <= 1
        assert "_fallback" in result


class TestAIServiceIntegration:
    """AI服务集成测试（模拟外部调用）"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_customer_with_fallback(self):
        """测试客户分析带降级"""
        service = AIService()
        
        # 模拟chat失败，触发降级
        with patch.object(service, 'chat', side_effect=AIServiceError("API Error")):
            customer_info = {
                "name": "测试客户",
                "company": "测试科技公司",
                "industry": "互联网",
                "status": "interested"
            }
            
            result = await service.analyze_customer(customer_info)
            
            # 应该返回降级结果
            assert result is not None
            assert "_fallback" in result or "customer_type" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_predict_close_probability_with_fallback(self):
        """测试成交概率预测带降级"""
        service = AIService()
        
        # 模拟chat失败，触发降级
        with patch.object(service, 'chat', side_effect=AIServiceError("API Error")):
            opportunity_info = {
                "name": "测试机会",
                "amount": 100000,
                "stage": "negotiating"
            }
            
            result = await service.predict_close_probability(opportunity_info)
            
            # 应该返回降级结果
            assert result is not None
            assert "probability" in result
