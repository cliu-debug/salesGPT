import httpx
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.logger import logger
import json
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

# 导入增强功能
from app.services.ai_enhancements import (
    AICacheManager,
    TokenMonitor,
    CustomerAnalysisFallback,
    QuoteSuggestionFallback,
    FollowUpScriptFallback,
    ProbabilityFallback
)


class AIServiceError(Exception):
    """AI服务异常"""
    pass


class AIService:
    """
    AI服务类 - 封装通义千问API调用
    
    特性：
    - 自动重试机制
    - 降级策略
    - 响应缓存
    - Token监控
    """
    
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.DASHSCOPE_MODEL
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        # 初始化增强功能
        self.cache = AICacheManager(default_ttl=3600)  # 1小时缓存
        self.token_monitor = TokenMonitor()
        
        # 初始化降级策略
        self.fallback_strategies = {
            "customer_analysis": CustomerAnalysisFallback(),
            "quote_suggestion": QuoteSuggestionFallback(),
            "followup_script": FollowUpScriptFallback(),
            "probability": ProbabilityFallback()
        }
        
        logger.info(f"AI服务初始化完成, 模型: {self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(AIServiceError),
        before_sleep=before_sleep_log(logger, logger.level)
    )
    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        user_id: Optional[int] = None,
        use_cache: bool = True
    ) -> str:
        """
        调用AI对话接口（带重试、缓存和监控）
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大Token数
            user_id: 用户ID（用于监控和配额）
            use_cache: 是否使用缓存
            
        Returns:
            AI响应文本
        """
        # 检查API密钥
        if not self.api_key or self.api_key == "your-dashscope-api-key":
            logger.warning("DASHSCOPE_API_KEY未配置")
            return "请配置DASHSCOPE_API_KEY以启用AI功能"
        
        # 检查缓存
        if use_cache:
            cached_result = await self.cache.get(
                "chat", prompt, system_prompt, temperature
            )
            if cached_result:
                logger.debug("从缓存返回AI响应")
                return cached_result
        
        # 检查Token配额
        if user_id:
            has_quota = await self.token_monitor.check_quota(user_id)
            if not has_quota:
                return "今日AI调用次数已达上限，请明天再试"
        
        # 准备请求
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {"messages": messages},
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url, 
                    headers=headers, 
                    json=payload
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("output", {}).get("text", "")
                    
                    # 记录Token使用
                    usage = result.get("usage", {})
                    if user_id and usage:
                        await self.token_monitor.record_usage(
                            user_id=user_id,
                            model=self.model,
                            prompt_tokens=usage.get("input_tokens", 0),
                            completion_tokens=usage.get("output_tokens", 0),
                            total_tokens=usage.get("total_tokens", 0),
                            duration_ms=duration_ms
                        )
                    
                    # 缓存结果
                    if use_cache:
                        await self.cache.set(
                            "chat", text, 
                            prompt, system_prompt, temperature
                        )
                    
                    logger.info(f"AI调用成功, 耗时: {duration_ms:.0f}ms")
                    return text
                else:
                    error_msg = f"AI调用失败: {response.status_code}"
                    logger.error(error_msg)
                    raise AIServiceError(error_msg)
                    
        except httpx.TimeoutException:
            logger.error("AI调用超时")
            raise AIServiceError("AI服务超时，请稍后重试")
        except Exception as e:
            logger.error(f"AI服务异常: {e}", exc_info=True)
            raise AIServiceError(f"AI服务异常: {str(e)}")
    
    async def analyze_customer_profile(
        self,
        customer_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"""
请分析以下客户信息，生成客户画像：

客户名称：{customer_info.get('name', '未知')}
公司：{customer_info.get('company', '未知')}
行业：{customer_info.get('industry', '未知')}
来源：{customer_info.get('source', '未知')}
备注：{customer_info.get('remark', '无')}

请从以下维度分析：
1. 客户类型（大客户/中小客户/潜在客户）
2. 预算等级（高/中/低）
3. 决策周期（快/中/慢）
4. 关注重点
5. 推荐策略

请以JSON格式返回结果。
"""
        result = await self.chat(prompt)
        return {
            "analysis": result,
            "customer_type": "待分析",
            "budget_level": "待分析",
            "decision_speed": "待分析",
            "focus_points": [],
            "recommended_strategy": result
        }
    
    async def analyze_customer(
        self,
        customer_info: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        分析客户画像（含历史跟进记录）
        
        特性：失败时自动降级到规则引擎
        """
        # 尝试从缓存获取
        cached = await self.cache.get("customer_analysis", customer_info)
        if cached:
            return cached
        
        history_text = ""
        if history:
            history_text = "\n历史跟进记录：\n" + "\n".join([
                f"- {h.get('content', '')}" for h in history[:5]
            ])
        
        prompt = f"""
请分析以下客户信息，生成客户画像：

客户名称：{customer_info.get('name', '未知')}
公司：{customer_info.get('company', '未知')}
行业：{customer_info.get('industry', '未知')}
来源：{customer_info.get('source', '未知')}
状态：{customer_info.get('status', '未知')}
备注：{customer_info.get('remark', '无')}
{history_text}

请从以下维度分析并以JSON格式返回：
{{
    "customer_type": "客户类型（大客户/中小客户/潜在客户）",
    "budget_level": "预算等级（高/中/低）",
    "decision_speed": "决策周期（快/中/慢）",
    "focus_points": ["关注重点1", "关注重点2"],
    "recommended_strategy": "推荐策略",
    "risk_assessment": "风险评估",
    "next_steps": ["下一步建议1", "下一步建议2"]
}}
"""
        
        try:
            result = await self.chat(prompt, user_id=user_id)
            
            try:
                if '{' in result:
                    start = result.index('{')
                    end = result.rindex('}') + 1
                    parsed = json.loads(result[start:end])
                    
                    # 缓存结果
                    await self.cache.set("customer_analysis", parsed, customer_info)
                    return parsed
            except:
                pass
            
            return {
                "customer_type": "待分析",
                "budget_level": "待分析",
                "decision_speed": "待分析",
                "focus_points": [],
                "recommended_strategy": result,
                "risk_assessment": "",
                "next_steps": []
            }
        except AIServiceError as e:
            # 降级到规则引擎
            logger.warning(f"AI分析失败，使用降级策略: {e}")
            return await self.fallback_strategies["customer_analysis"].execute(customer_info)
    
    async def suggest_quote_price(
        self,
        customer_info: Dict[str, Any],
        product_info: List[Dict[str, Any]],
        historical_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        报价建议
        
        特性：失败时自动降级到规则引擎
        """
        prompt = f"""
请根据以下信息，给出报价建议：

客户信息：
- 名称：{customer_info.get('name', '未知')}
- 公司：{customer_info.get('company', '未知')}
- 行业：{customer_info.get('industry', '未知')}

产品信息：
{json.dumps(product_info, ensure_ascii=False, indent=2)}

历史数据：
{json.dumps(historical_data, ensure_ascii=False, indent=2) if historical_data else '无历史数据'}

请给出：
1. 建议折扣比例
2. 报价策略
3. 成交概率预估
4. 谈判要点
"""
        
        try:
            result = await self.chat(prompt, user_id=user_id)
            
            try:
                if '{' in result:
                    start = result.index('{')
                    end = result.rindex('}') + 1
                    return json.loads(result[start:end])
            except:
                pass
            
            return {
                "suggestion": result,
                "recommended_discount": "待分析",
                "strategy": result,
                "win_probability": 0.5
            }
        except AIServiceError as e:
            # 降级到规则引擎
            logger.warning(f"AI报价建议失败，使用降级策略: {e}")
            return await self.fallback_strategies["quote_suggestion"].execute(
                customer_info, product_info
            )
    
    async def generate_follow_up_script(
        self,
        customer_info: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        purpose: str = "日常跟进",
        user_id: Optional[int] = None
    ) -> str:
        """
        生成跟进话术
        
        特性：失败时自动降级到模板生成
        """
        history_text = ""
        if history:
            history_text = "\n历史跟进记录：\n" + "\n".join([
                f"- {h.get('content', '')}" for h in history[:5]
            ])
        
        prompt = f"""
请为以下客户生成跟进话术：

客户信息：
- 名称：{customer_info.get('name', '未知')}
- 公司：{customer_info.get('company', '未知')}
- 当前状态：{customer_info.get('status', '未知')}
- 行业：{customer_info.get('industry', '未知')}
{history_text}

跟进目的：{purpose}

请生成一段专业、自然的跟进话术，包含：
1. 开场白
2. 核心内容
3. 引导下一步行动
"""
        
        try:
            return await self.chat(prompt, user_id=user_id)
        except AIServiceError as e:
            # 降级到模板
            logger.warning(f"AI生成话术失败，使用降级策略: {e}")
            return await self.fallback_strategies["followup_script"].execute(customer_info)
    
    async def predict_win_probability(
        self,
        opportunity_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"""
请预测以下销售机会的成交概率：

机会信息：
- 名称：{opportunity_info.get('name', '未知')}
- 金额：{opportunity_info.get('amount', 0)}
- 当前阶段：{opportunity_info.get('stage', '未知')}
- 预计成交日期：{opportunity_info.get('expected_date', '未知')}

请给出：
1. 成交概率（0-100%）
2. 关键风险点
3. 推进建议
"""
        result = await self.chat(prompt)
        return {
            "probability": 0.5,
            "analysis": result,
            "risks": [],
            "suggestions": result
        }
    
    async def predict_close_probability(
        self,
        opportunity_info: Dict[str, Any],
        customer_info: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        预测成交概率（含客户信息）
        
        特性：失败时自动降级到规则预测
        """
        customer_text = ""
        if customer_info:
            customer_text = f"""
客户信息：
- 名称：{customer_info.get('name', '未知')}
- 公司：{customer_info.get('company', '未知')}
- 行业：{customer_info.get('industry', '未知')}
- 状态：{customer_info.get('status', '未知')}
"""
        
        prompt = f"""
请预测以下销售机会的成交概率：

机会信息：
- 名称：{opportunity_info.get('name', '未知')}
- 金额：{opportunity_info.get('amount', 0)}
- 当前阶段：{opportunity_info.get('stage', '未知')}
- 预计成交日期：{opportunity_info.get('expected_date', '未知')}
{customer_text}

请分析并返回JSON格式结果：
{{
    "probability": 0.5,
    "confidence": "置信度（高/中/低）",
    "key_factors": ["关键因素1", "关键因素2"],
    "risks": ["风险1", "风险2"],
    "suggestions": ["建议1", "建议2"],
    "next_actions": ["下一步行动1", "下一步行动2"]
}}
"""
        
        try:
            result = await self.chat(prompt, user_id=user_id)
            
            try:
                if '{' in result:
                    start = result.index('{')
                    end = result.rindex('}') + 1
                    parsed = json.loads(result[start:end])
                    if "probability" in parsed:
                        parsed["probability"] = float(parsed.get("probability", 0.5))
                    return parsed
            except:
                pass
            
            return {
                "probability": 0.5,
                "confidence": "中",
                "key_factors": [],
                "risks": [],
                "suggestions": [result],
                "next_actions": []
            }
        except AIServiceError as e:
            # 降级到规则预测
            logger.warning(f"AI预测失败，使用降级策略: {e}")
            return await self.fallback_strategies["probability"].execute(opportunity_info)
    
    async def sales_forecast(
        self,
        historical_data: Dict[str, Any],
        current_pipeline: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        销售预测 - 预测未来销售额和成交情况
        """
        system_prompt = """你是一个专业的销售预测分析师。请根据历史数据和当前销售漏斗，
预测未来销售额、成交概率和关键风险。请以JSON格式返回结果。"""
        
        prompt = f"""
请根据以下数据进行销售预测：

历史销售数据：
{json.dumps(historical_data, ensure_ascii=False, indent=2)}

当前销售漏斗：
{json.dumps(current_pipeline, ensure_ascii=False, indent=2)}

请预测并返回以下内容（JSON格式）：
{{
    "monthly_forecast": {{
        "next_month": {{"amount": 预测金额, "confidence": 置信度}},
        "next_quarter": {{"amount": 预测金额, "confidence": 置信度}}
    }},
    "pipeline_analysis": {{
        "total_value": 漏斗总价值,
        "weighted_value": 加权预测值,
        "conversion_prediction": 预计转化数量
    }},
    "key_insights": ["洞察1", "洞察2", "洞察3"],
    "risks": ["风险1", "风险2"],
    "recommendations": ["建议1", "建议2", "建议3"]
}}
"""
        result = await self.chat(prompt, system_prompt)
        
        try:
            if '{' in result:
                start = result.index('{')
                end = result.rindex('}') + 1
                return json.loads(result[start:end])
        except:
            pass
        
        return {
            "monthly_forecast": {
                "next_month": {"amount": 0, "confidence": 0},
                "next_quarter": {"amount": 0, "confidence": 0}
            },
            "pipeline_analysis": {
                "total_value": 0,
                "weighted_value": 0,
                "conversion_prediction": 0
            },
            "key_insights": [result],
            "risks": [],
            "recommendations": []
        }
    
    async def smart_recommendation(
        self,
        user_context: Dict[str, Any],
        customers: List[Dict[str, Any]],
        opportunities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        智能推荐 - 推荐今日重点跟进客户和行动建议
        """
        system_prompt = """你是一个资深销售顾问。请根据用户当前情况和客户数据，
给出今日工作重点和跟进建议。"""
        
        prompt = f"""
用户当前情况：
{json.dumps(user_context, ensure_ascii=False, indent=2)}

客户列表：
{json.dumps(customers[:10], ensure_ascii=False, indent=2)}

销售机会：
{json.dumps(opportunities[:10], ensure_ascii=False, indent=2)}

请给出今日工作建议（JSON格式）：
{{
    "priority_customers": [
        {{"customer_id": ID, "reason": "原因", "action": "建议行动"}}
    ],
    "priority_opportunities": [
        {{"opportunity_id": ID, "reason": "原因", "action": "建议行动"}}
    ],
    "daily_focus": ["重点1", "重点2", "重点3"],
    "quick_wins": ["快速成交建议1", "快速成交建议2"],
    "risk_alerts": ["风险提醒1", "风险提醒2"]
}}
"""
        result = await self.chat(prompt, system_prompt)
        
        try:
            if '{' in result:
                start = result.index('{')
                end = result.rindex('}') + 1
                return json.loads(result[start:end])
        except:
            pass
        
        return {
            "priority_customers": [],
            "priority_opportunities": [],
            "daily_focus": [result],
            "quick_wins": [],
            "risk_alerts": []
        }
    
    async def generate_sales_report(
        self,
        stats: Dict[str, Any],
        period: str = "本周"
    ) -> str:
        """
        生成销售报告
        """
        system_prompt = "你是一个专业的销售数据分析专家，擅长撰写简洁有力的销售报告。"
        
        prompt = f"""
请根据以下数据生成{period}销售报告：

数据统计：
{json.dumps(stats, ensure_ascii=False, indent=2)}

请生成一份简洁的销售报告，包含：
1. 核心数据总结
2. 主要亮点
3. 需要关注的问题
4. 下周工作建议

报告风格：专业、简洁、有洞察力。
"""
        return await self.chat(prompt, system_prompt)
    
    async def analyze_lost_reason(
        self,
        lost_opportunities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析丢单原因
        """
        system_prompt = "你是一个销售分析专家，擅长从失败案例中总结经验教训。"
        
        prompt = f"""
请分析以下丢单案例，总结失败原因：

丢单案例：
{json.dumps(lost_opportunities, ensure_ascii=False, indent=2)}

请分析并返回（JSON格式）：
{{
    "main_reasons": [
        {{"reason": "原因", "count": 数量, "percentage": 百分比}}
    ],
    "patterns": ["发现的模式1", "发现的模式2"],
    "improvement_suggestions": ["改进建议1", "改进建议2", "改进建议3"],
    "training_needs": ["需要培训的领域1", "需要培训的领域2"]
}}
"""
        result = await self.chat(prompt, system_prompt)
        
        try:
            if '{' in result:
                start = result.index('{')
                end = result.rindex('}') + 1
                return json.loads(result[start:end])
        except:
            pass
        
        return {
            "main_reasons": [],
            "patterns": [],
            "improvement_suggestions": [result],
            "training_needs": []
        }
    
    async def get_sales_insights(
        self,
        dashboard_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取销售洞察
        """
        system_prompt = "你是一个资深的销售管理顾问，擅长从数据中发现洞察并给出可执行的建议。"
        
        prompt = f"""
请分析以下销售数据，给出洞察和建议：

销售数据：
{json.dumps(dashboard_data, ensure_ascii=False, indent=2)}

请分析并返回（JSON格式）：
{{
    "summary": "数据概要（一句话总结）",
    "highlights": ["亮点1", "亮点2"],
    "concerns": ["关注点1", "关注点2"],
    "recommendations": ["建议1", "建议2", "建议3"],
    "priority_actions": ["优先行动1", "优先行动2"]
}}
"""
        result = await self.chat(prompt, system_prompt)
        
        try:
            if '{' in result:
                start = result.index('{')
                end = result.rindex('}') + 1
                return json.loads(result[start:end])
        except:
            pass
        
        return {
            "summary": result,
            "highlights": [],
            "concerns": [],
            "recommendations": [],
            "priority_actions": []
        }


ai_service = AIService()
