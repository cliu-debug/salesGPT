"""
查询优化模块 - 提供常用查询的优化实现
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.models import (
    Customer, Opportunity, Quote, FollowUp,
    User, DashboardStats, AgentAlert
)


class QueryOptimizer:
    """查询优化器"""
    
    @staticmethod
    async def get_customer_list_optimized(
        db: AsyncSession,
        organization_id: int,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        industry: Optional[str] = None,
        source: Optional[str] = None
    ) -> tuple[List[Customer], int]:
        """
        优化的客户列表查询
        
        使用索引: ix_customers_org_industry, ix_customers_org_source
        """
        # 基础查询
        query = select(Customer).where(
            Customer.organization_id == organization_id
        )
        
        # 条件过滤
        conditions = []
        
        if search:
            # 使用全文搜索或模糊匹配
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    Customer.name.ilike(search_pattern),
                    Customer.contact.ilike(search_pattern),
                    Customer.company.ilike(search_pattern),
                    Customer.phone.ilike(search_pattern)
                )
            )
        
        if industry:
            conditions.append(Customer.industry == industry)
        
        if source:
            conditions.append(Customer.source == source)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 统计总数（优化：不加载全部数据）
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # 分页获取数据
        query = query.order_by(Customer.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        customers = list(result.scalars().all())
        
        return customers, total
    
    @staticmethod
    async def get_opportunity_list_optimized(
        db: AsyncSession,
        organization_id: int,
        skip: int = 0,
        limit: int = 20,
        stage: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None
    ) -> tuple[List[Opportunity], int]:
        """
        优化的销售机会列表查询
        
        使用索引: ix_opportunities_org_stage, ix_opportunities_org_amount
        """
        query = select(Opportunity).where(
            Opportunity.organization_id == organization_id
        )
        
        conditions = []
        
        if stage:
            conditions.append(Opportunity.stage == stage)
        
        if min_amount is not None:
            conditions.append(Opportunity.amount >= min_amount)
        
        if max_amount is not None:
            conditions.append(Opportunity.amount <= max_amount)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # 分页获取
        query = query.order_by(Opportunity.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        opportunities = list(result.scalars().all())
        
        return opportunities, total
    
    @staticmethod
    async def get_dashboard_stats_optimized(
        db: AsyncSession,
        organization_id: int,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        优化的仪表盘统计查询
        
        使用预计算统计表或缓存
        """
        from app.services.cache_service import get_cache_service
        
        # 尝试从缓存获取
        if use_cache:
            cache = get_cache_service()
            cached = await cache.get("dashboard", organization_id)
            if cached:
                return cached
        
        # 并行执行多个统计查询
        today = datetime.now().date()
        
        # 客户统计
        customer_count_query = select(func.count(Customer.id)).where(
            Customer.organization_id == organization_id
        )
        total_customers = await db.scalar(customer_count_query) or 0
        
        # 机会统计
        opportunity_stats_query = select(
            func.count(Opportunity.id).label("count"),
            func.sum(Opportunity.amount).label("total_amount"),
            func.sum(Opportunity.amount * Opportunity.probability / 100).label("weighted_amount")
        ).where(Opportunity.organization_id == organization_id)
        
        opp_stats = (await db.execute(opportunity_stats_query)).one()
        
        # 阶段分布
        stage_dist_query = select(
            Opportunity.stage,
            func.count(Opportunity.id).label("count"),
            func.sum(Opportunity.amount).label("amount")
        ).where(
            Opportunity.organization_id == organization_id
        ).group_by(Opportunity.stage)
        
        stage_distribution = {}
        for row in await db.execute(stage_dist_query):
            stage_distribution[row.stage] = {
                "count": row.count,
                "amount": float(row.amount or 0)
            }
        
        # 成交统计
        won_query = select(
            func.count(Opportunity.id).label("count"),
            func.sum(Opportunity.amount).label("amount")
        ).where(
            and_(
                Opportunity.organization_id == organization_id,
                Opportunity.stage == "closed_won"
            )
        )
        won_stats = (await db.execute(won_query)).one()
        
        # 计算转化率
        total_opportunities = opp_stats.count or 0
        won_count = won_stats.count or 0
        conversion_rate = (won_count / total_opportunities * 100) if total_opportunities > 0 else 0
        
        result = {
            "total_customers": total_customers,
            "total_opportunities": total_opportunities,
            "total_amount": float(opp_stats.total_amount or 0),
            "weighted_amount": float(opp_stats.weighted_amount or 0),
            "conversion_rate": round(conversion_rate, 2),
            "stage_distribution": stage_distribution,
            "won_count": won_count,
            "won_amount": float(won_stats.amount or 0)
        }
        
        # 缓存结果
        if use_cache:
            cache = get_cache_service()
            await cache.set("dashboard", result, ttl=60, organization_id=organization_id)
        
        return result
    
    @staticmethod
    async def get_funnel_stats_optimized(
        db: AsyncSession,
        organization_id: int
    ) -> List[Dict[str, Any]]:
        """
        优化的销售漏斗统计
        
        使用单次查询获取所有阶段统计
        """
        # 定义阶段顺序和概率
        stage_config = {
            "initial": {"name": "初步接触", "probability": 20, "order": 1},
            "need_confirm": {"name": "需求确认", "probability": 40, "order": 2},
            "quoting": {"name": "方案报价", "probability": 50, "order": 3},
            "negotiating": {"name": "商务谈判", "probability": 70, "order": 4},
            "closed_won": {"name": "成交", "probability": 100, "order": 5},
            "closed_lost": {"name": "失败", "probability": 0, "order": 6}
        }
        
        # 单次查询获取所有阶段数据
        query = select(
            Opportunity.stage,
            func.count(Opportunity.id).label("count"),
            func.sum(Opportunity.amount).label("amount"),
            func.sum(Opportunity.amount * Opportunity.probability / 100).label("weighted_amount")
        ).where(
            and_(
                Opportunity.organization_id == organization_id,
                Opportunity.stage.notin_(["closed_lost"])
            )
        ).group_by(Opportunity.stage)
        
        result = await db.execute(query)
        
        # 构建漏斗数据
        funnel = []
        for row in result:
            config = stage_config.get(row.stage, {})
            funnel.append({
                "stage": row.stage,
                "stage_name": config.get("name", row.stage),
                "count": row.count,
                "amount": float(row.amount or 0),
                "weighted_amount": float(row.weighted_amount or 0),
                "probability": config.get("probability", 0),
                "order": config.get("order", 0)
            })
        
        # 按阶段顺序排序
        funnel.sort(key=lambda x: x["order"])
        
        return funnel
    
    @staticmethod
    async def get_alerts_optimized(
        db: AsyncSession,
        organization_id: int,
        user_id: Optional[int] = None,
        unread_only: bool = False
    ) -> List[AgentAlert]:
        """
        优化的预警查询
        
        使用索引: ix_agent_alerts_org_unread
        """
        query = select(AgentAlert).where(
            AgentAlert.organization_id == organization_id
        )
        
        if user_id:
            query = query.where(AgentAlert.user_id == user_id)
        
        if unread_only:
            query = query.where(AgentAlert.is_read == False)
        
        query = query.order_by(AgentAlert.created_at.desc())
        query = query.limit(50)  # 限制返回数量
        
        result = await db.execute(query)
        return list(result.scalars().all())


# 批量操作优化
class BatchOperations:
    """批量操作优化"""
    
    @staticmethod
    async def batch_create_customers(
        db: AsyncSession,
        customers_data: List[Dict[str, Any]],
        organization_id: int,
        created_by: int
    ) -> List[Customer]:
        """
        批量创建客户（优化版）
        
        使用批量插入代替逐条插入
        """
        customers = []
        for data in customers_data:
            customer = Customer(
                **data,
                organization_id=organization_id,
                created_by=created_by
            )
            customers.append(customer)
        
        # 批量添加
        db.add_all(customers)
        await db.commit()
        
        # 刷新获取ID
        for customer in customers:
            await db.refresh(customer)
        
        return customers
    
    @staticmethod
    async def batch_update_opportunity_stage(
        db: AsyncSession,
        updates: List[Dict[str, Any]]
    ) -> int:
        """
        批量更新机会阶段
        
        使用批量更新语句
        """
        from sqlalchemy import update
        
        count = 0
        for update_data in updates:
            stmt = update(Opportunity).where(
                Opportunity.id == update_data["id"]
            ).values(
                stage=update_data["stage"],
                probability=update_data.get("probability")
            )
            result = await db.execute(stmt)
            count += result.rowcount
        
        await db.commit()
        return count
