"""
智能体决策优化器 - 实现学习机制和A/B测试
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from app.models.models import AgentMemory, AgentTask, AgentGoal
import json
import logging
import hashlib

logger = logging.getLogger(__name__)


class DecisionOutcome(str, Enum):
    """决策结果"""
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    PENDING = "pending"


class StrategyType(str, Enum):
    """策略类型（用于A/B测试）"""
    AGGRESSIVE = "aggressive"  # 激进策略
    CONSERVATIVE = "conservative"  # 保守策略
    BALANCED = "balanced"  # 平衡策略


class DecisionOptimizer:
    """
    决策优化器
    
    功能：
    1. 决策成功率统计
    2. 反馈驱动权重调整
    3. A/B测试框架
    4. 策略自动选择
    """
    
    def __init__(self, db: AsyncSession, organization_id: int):
        self.db = db
        self.organization_id = organization_id
        
        # 权重配置
        self.weights = {
            "customer_followup": 1.0,
            "opportunity_advance": 1.0,
            "quote_creation": 1.0,
            "risk_alert": 1.0,
        }
        
        # 学习率
        self.learning_rate = 0.1
        
        # 权重调整范围
        self.min_weight = 0.5
        self.max_weight = 1.5
    
    async def record_decision(
        self,
        decision_type: str,
        action: str,
        target: str,
        outcome: DecisionOutcome,
        context: Optional[Dict] = None,
        strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        记录决策及其结果
        
        Args:
            decision_type: 决策类型
            action: 执行的动作
            target: 目标对象
            outcome: 决策结果
            context: 上下文信息
            strategy: 使用的策略（A/B测试）
        
        Returns:
            记录结果和统计数据
        """
        # 存储决策记录到记忆系统
        memory = AgentMemory(
            memory_type="decision_record",
            entity_type="decision",
            title=f"{decision_type}: {outcome.value}",
            content=json.dumps({
                "decision_type": decision_type,
                "action": action,
                "target": target,
                "outcome": outcome.value,
                "context": context or {},
                "strategy": strategy,
                "timestamp": datetime.now().isoformat()
            }),
            importance=0.8 if outcome == DecisionOutcome.SUCCESS else 0.6,
            organization_id=self.organization_id
        )
        
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        
        # 更新权重
        await self._update_weights(decision_type, outcome)
        
        # 记录A/B测试结果
        if strategy:
            await self._record_ab_test_result(strategy, outcome)
        
        # 获取最新统计
        stats = await self.get_decision_stats(decision_type)
        
        logger.info(f"决策已记录: {decision_type} -> {outcome.value}, 成功率: {stats['success_rate']:.1%}")
        
        return {
            "decision_id": memory.id,
            "outcome": outcome.value,
            "stats": stats
        }
    
    async def _update_weights(self, decision_type: str, outcome: DecisionOutcome):
        """
        根据决策结果更新权重
        
        使用简单的强化学习算法：
        - 成功：权重 *= (1 + learning_rate)
        - 失败：权重 *= (1 - learning_rate)
        - 中性：权重不变
        """
        if decision_type not in self.weights:
            self.weights[decision_type] = 1.0
        
        old_weight = self.weights[decision_type]
        
        if outcome == DecisionOutcome.SUCCESS:
            adjustment = 1 + self.learning_rate
        elif outcome == DecisionOutcome.FAILURE:
            adjustment = 1 - self.learning_rate
        else:
            adjustment = 1.0
        
        new_weight = old_weight * adjustment
        
        # 限制权重范围
        new_weight = max(self.min_weight, min(self.max_weight, new_weight))
        
        self.weights[decision_type] = new_weight
        
        logger.debug(
            f"权重调整: {decision_type} {old_weight:.2f} -> {new_weight:.2f} "
            f"(调整: {adjustment:.2f})"
        )
        
        # 持久化权重到数据库
        await self._save_weights()
    
    async def _save_weights(self):
        """保存权重到数据库"""
        weight_memory = AgentMemory(
            memory_type="system_config",
            entity_type="weights",
            title="决策权重配置",
            content=json.dumps(self.weights),
            importance=1.0,
            organization_id=self.organization_id
        )
        
        # 检查是否已存在权重配置
        existing_query = select(AgentMemory).where(
            and_(
                AgentMemory.memory_type == "system_config",
                AgentMemory.entity_type == "weights",
                AgentMemory.organization_id == self.organization_id
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            existing.content = json.dumps(self.weights)
        else:
            self.db.add(weight_memory)
        
        await self.db.commit()
    
    async def load_weights(self):
        """从数据库加载权重"""
        query = select(AgentMemory).where(
            and_(
                AgentMemory.memory_type == "system_config",
                AgentMemory.entity_type == "weights",
                AgentMemory.organization_id == self.organization_id
            )
        ).order_by(desc(AgentMemory.created_at)).limit(1)
        
        result = await self.db.execute(query)
        memory = result.scalar_one_or_none()
        
        if memory:
            try:
                self.weights = json.loads(memory.content)
                logger.info(f"已加载权重配置: {self.weights}")
            except Exception as e:
                logger.error(f"加载权重失败: {e}")
    
    async def get_decision_stats(
        self,
        decision_type: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取决策统计
        
        Args:
            decision_type: 决策类型（None表示所有类型）
            days: 统计天数
        
        Returns:
            统计数据
        """
        start_date = datetime.now() - timedelta(days=days)
        
        # 查询决策记录
        query = select(AgentMemory).where(
            and_(
                AgentMemory.memory_type == "decision_record",
                AgentMemory.organization_id == self.organization_id,
                AgentMemory.created_at >= start_date
            )
        )
        
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        # 统计
        total = len(records)
        success_count = 0
        failure_count = 0
        neutral_count = 0
        
        decision_type_stats = {}
        
        for record in records:
            try:
                data = json.loads(record.content)
                outcome = data.get("outcome")
                dtype = data.get("decision_type")
                
                if outcome == DecisionOutcome.SUCCESS.value:
                    success_count += 1
                elif outcome == DecisionOutcome.FAILURE.value:
                    failure_count += 1
                else:
                    neutral_count += 1
                
                # 按类型统计
                if dtype:
                    if dtype not in decision_type_stats:
                        decision_type_stats[dtype] = {
                            "total": 0,
                            "success": 0,
                            "failure": 0
                        }
                    decision_type_stats[dtype]["total"] += 1
                    if outcome == DecisionOutcome.SUCCESS.value:
                        decision_type_stats[dtype]["success"] += 1
                    elif outcome == DecisionOutcome.FAILURE.value:
                        decision_type_stats[dtype]["failure"] += 1
                        
            except Exception as e:
                logger.error(f"解析决策记录失败: {e}")
        
        # 如果指定了决策类型，过滤统计
        if decision_type and decision_type in decision_type_stats:
            type_stats = decision_type_stats[decision_type]
            return {
                "decision_type": decision_type,
                "total": type_stats["total"],
                "success": type_stats["success"],
                "failure": type_stats["failure"],
                "success_rate": type_stats["success"] / type_stats["total"] if type_stats["total"] > 0 else 0,
                "weight": self.weights.get(decision_type, 1.0),
                "period_days": days
            }
        
        # 返回总体统计
        return {
            "total": total,
            "success": success_count,
            "failure": failure_count,
            "neutral": neutral_count,
            "success_rate": success_count / total if total > 0 else 0,
            "decision_types": decision_type_stats,
            "weights": self.weights,
            "period_days": days
        }
    
    async def _record_ab_test_result(
        self,
        strategy: str,
        outcome: DecisionOutcome
    ):
        """
        记录A/B测试结果
        
        Args:
            strategy: 策略名称
            outcome: 决策结果
        """
        # 存储A/B测试结果
        ab_test_memory = AgentMemory(
            memory_type="ab_test_result",
            entity_type="strategy",
            title=f"策略测试: {strategy}",
            content=json.dumps({
                "strategy": strategy,
                "outcome": outcome.value,
                "timestamp": datetime.now().isoformat()
            }),
            importance=0.7,
            organization_id=self.organization_id
        )
        
        self.db.add(ab_test_memory)
        await self.db.commit()
    
    async def get_ab_test_stats(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取A/B测试统计
        
        Returns:
            各策略的成功率统计
        """
        start_date = datetime.now() - timedelta(days=days)
        
        query = select(AgentMemory).where(
            and_(
                AgentMemory.memory_type == "ab_test_result",
                AgentMemory.organization_id == self.organization_id,
                AgentMemory.created_at >= start_date
            )
        )
        
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        # 按策略统计
        strategy_stats = {}
        
        for record in records:
            try:
                data = json.loads(record.content)
                strategy = data.get("strategy")
                outcome = data.get("outcome")
                
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {
                        "total": 0,
                        "success": 0,
                        "failure": 0
                    }
                
                strategy_stats[strategy]["total"] += 1
                if outcome == DecisionOutcome.SUCCESS.value:
                    strategy_stats[strategy]["success"] += 1
                elif outcome == DecisionOutcome.FAILURE.value:
                    strategy_stats[strategy]["failure"] += 1
                    
            except Exception as e:
                logger.error(f"解析A/B测试记录失败: {e}")
        
        # 计算成功率
        for strategy, stats in strategy_stats.items():
            stats["success_rate"] = (
                stats["success"] / stats["total"] 
                if stats["total"] > 0 
                else 0
            )
        
        # 找出最佳策略
        best_strategy = None
        best_rate = 0
        
        for strategy, stats in strategy_stats.items():
            if stats["success_rate"] > best_rate:
                best_rate = stats["success_rate"]
                best_strategy = strategy
        
        return {
            "strategies": strategy_stats,
            "best_strategy": best_strategy,
            "best_success_rate": best_rate,
            "period_days": days,
            "total_tests": sum(s["total"] for s in strategy_stats.values())
        }
    
    async def select_best_strategy(self) -> str:
        """
        选择当前最佳策略
        
        基于A/B测试结果，自动选择成功率最高的策略
        """
        stats = await self.get_ab_test_stats(days=7)
        
        if stats["best_strategy"]:
            logger.info(f"选择最佳策略: {stats['best_strategy']}, 成功率: {stats['best_success_rate']:.1%}")
            return stats["best_strategy"]
        
        # 默认使用平衡策略
        return StrategyType.BALANCED.value
    
    def get_weighted_score(self, decision_type: str, base_score: float) -> float:
        """
        获取加权后的决策分数
        
        Args:
            decision_type: 决策类型
            base_score: 基础分数
        
        Returns:
            加权后的分数
        """
        weight = self.weights.get(decision_type, 1.0)
        weighted_score = base_score * weight
        
        logger.debug(
            f"加权分数: {decision_type} {base_score:.2f} * {weight:.2f} = {weighted_score:.2f}"
        )
        
        return weighted_score
    
    async def normalize_weights(self):
        """
        归一化权重
        
        确保权重总和为 1，避免权重过大或过小
        """
        total_weight = sum(self.weights.values())
        
        if total_weight > 0:
            for key in self.weights:
                self.weights[key] = (
                    self.weights[key] / total_weight * len(self.weights)
                )
        
        # 限制范围
        for key in self.weights:
            self.weights[key] = max(
                self.min_weight,
                min(self.max_weight, self.weights[key])
            )
        
        await self._save_weights()
        logger.info(f"权重已归一化: {self.weights}")
