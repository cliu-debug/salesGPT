"""
分析Agent服务 - 深度分析销售数据
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from app.models.models import (
    Customer, Opportunity, Quote, FollowUp,
    AgentMemory, AgentTask, AgentAlert
)
from app.services.ai_service import ai_service
from app.services.memory_service import MemoryService
from app.core.logger import logger


class AnalysisAgent:
    """
    分析Agent - 深度分析销售数据，提供洞察和建议
    
    分析能力:
    1. 客户分析 - 客户价值评估、行为分析
    2. 机会分析 - 成交概率预测、风险评估
    3. 销售漏斗分析 - 转化率、瓶颈识别
    4. 趋势分析 - 销售趋势、周期性分析
    5. 竞争分析 - 丢单原因分析
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)
    
    async def analyze_customer_value(
        self,
        customer_id: int
    ) -> Dict[str, Any]:
        """
        分析客户价值
        """
        customer_query = select(Customer).where(Customer.id == customer_id)
        result = await self.db.execute(customer_query)
        customer = result.scalar_one_or_none()
        
        if not customer:
            return {"error": "客户不存在"}
        
        opps_query = select(Opportunity).where(
            Opportunity.customer_id == customer_id
        )
        opps_result = await self.db.execute(opps_query)
        opportunities = opps_result.scalars().all()
        
        total_amount = sum(o.amount or 0 for o in opportunities)
        won_amount = sum(o.amount or 0 for o in opportunities if o.stage == "closed_won")
        won_count = len([o for o in opportunities if o.stage == "closed_won"])
        lost_count = len([o for o in opportunities if o.stage == "closed_lost"])
        
        win_rate = won_count / (won_count + lost_count) if (won_count + lost_count) > 0 else 0
        
        quotes_query = select(Quote).where(Quote.customer_id == customer_id)
        quotes_result = await self.db.execute(quotes_query)
        quotes = quotes_result.scalars().all()
        
        quote_total = sum(q.total_amount or 0 for q in quotes)
        accepted_quotes = len([q for q in quotes if q.status == "accepted"])
        
        followups_query = select(FollowUp).where(FollowUp.customer_id == customer_id)
        followups_result = await self.db.execute(followups_query)
        followups = followups_result.scalars().all()
        
        followup_count = len(followups)
        avg_days_between = 0
        if len(followups) > 1:
            dates = sorted([f.created_at for f in followups if f.created_at])
            if len(dates) > 1:
                total_days = sum((dates[i+1] - dates[i]).days for i in range(len(dates)-1))
                avg_days_between = total_days / (len(dates) - 1)
        
        value_score = self._calculate_customer_value_score(
            total_amount=total_amount,
            won_amount=won_amount,
            win_rate=win_rate,
            followup_count=followup_count,
            quote_acceptance_rate=accepted_quotes / len(quotes) if quotes else 0
        )
        
        analysis = {
            "customer_id": customer_id,
            "customer_name": customer.name,
            "value_metrics": {
                "total_opportunity_amount": total_amount,
                "won_amount": won_amount,
                "win_rate": win_rate,
                "opportunity_count": len(opportunities),
                "won_count": won_count,
                "lost_count": lost_count
            },
            "engagement_metrics": {
                "total_quotes": len(quotes),
                "quote_total": quote_total,
                "accepted_quotes": accepted_quotes,
                "followup_count": followup_count,
                "avg_days_between_followups": avg_days_between
            },
            "value_score": value_score,
            "value_level": self._get_value_level(value_score),
            "recommendations": []
        }
        
        if value_score >= 80:
            analysis["recommendations"].append("高价值客户，建议重点维护，定期高层拜访")
        elif value_score >= 50:
            analysis["recommendations"].append("中等价值客户，有提升空间，建议深入了解需求")
        else:
            analysis["recommendations"].append("潜在价值待开发，建议培育客户关系")
        
        if win_rate < 0.3 and len(opportunities) > 2:
            analysis["recommendations"].append("成交率较低，建议分析丢单原因，优化销售策略")
        
        if avg_days_between > 14:
            analysis["recommendations"].append("跟进频率较低，建议增加互动频次")
        
        await self.memory_service.store_knowledge(
            entity_type="customer",
            entity_id=customer_id,
            knowledge_type="value_analysis",
            content=f"客户价值评分: {value_score}, 价值等级: {analysis['value_level']}, 总金额: {total_amount}",
            importance=0.8
        )
        
        return analysis
    
    def _calculate_customer_value_score(
        self,
        total_amount: float,
        won_amount: float,
        win_rate: float,
        followup_count: int,
        quote_acceptance_rate: float
    ) -> float:
        """
        计算客户价值评分 (0-100)
        """
        score = 0
        
        if total_amount >= 500000:
            score += 30
        elif total_amount >= 100000:
            score += 20
        elif total_amount >= 50000:
            score += 10
        
        score += win_rate * 25
        
        if followup_count >= 10:
            score += 15
        elif followup_count >= 5:
            score += 10
        elif followup_count >= 2:
            score += 5
        
        score += quote_acceptance_rate * 20
        
        score += won_amount / 100000 * 10
        
        return min(100, round(score, 1))
    
    def _get_value_level(self, score: float) -> str:
        """
        获取价值等级
        """
        if score >= 80:
            return "高价值"
        elif score >= 50:
            return "中等价值"
        elif score >= 30:
            return "潜在价值"
        else:
            return "待开发"
    
    async def analyze_sales_funnel(self) -> Dict[str, Any]:
        """
        分析销售漏斗
        """
        stages = ["initial", "need_confirm", "quoting", "negotiating", "closed_won", "closed_lost"]
        stage_data = {}
        
        for stage in stages:
            query = select(
                func.count(Opportunity.id).label('count'),
                func.sum(Opportunity.amount).label('amount')
            ).where(Opportunity.stage == stage)
            
            result = await self.db.execute(query)
            row = result.one()
            
            stage_data[stage] = {
                "count": row.count or 0,
                "amount": row.amount or 0
            }
        
        total_opportunities = sum(d["count"] for d in stage_data.values())
        total_amount = sum(d["amount"] for d in stage_data.values())
        
        conversion_rates = {}
        for i, stage in enumerate(stages[:-2]):
            current_count = stage_data[stage]["count"]
            next_count = stage_data[stages[i+1]]["count"]
            
            if current_count > 0:
                conversion_rates[f"{stage}_to_{stages[i+1]}"] = next_count / current_count
            else:
                conversion_rates[f"{stage}_to_{stages[i+1]}"] = 0
        
        overall_conversion = 0
        if stage_data["initial"]["count"] > 0:
            overall_conversion = stage_data["closed_won"]["count"] / stage_data["initial"]["count"]
        
        bottlenecks = []
        avg_conversion = sum(conversion_rates.values()) / len(conversion_rates) if conversion_rates else 0
        
        for transition, rate in conversion_rates.items():
            if rate < avg_conversion * 0.5:
                bottlenecks.append({
                    "transition": transition,
                    "rate": rate,
                    "issue": "转化率显著低于平均水平"
                })
        
        analysis = {
            "total_opportunities": total_opportunities,
            "total_amount": total_amount,
            "stage_data": stage_data,
            "conversion_rates": conversion_rates,
            "overall_conversion": overall_conversion,
            "bottlenecks": bottlenecks,
            "recommendations": []
        }
        
        if bottlenecks:
            analysis["recommendations"].append(f"发现 {len(bottlenecks)} 个漏斗瓶颈，建议重点优化")
        
        if overall_conversion < 0.1:
            analysis["recommendations"].append("整体转化率较低，建议审查销售流程")
        
        if stage_data["negotiating"]["count"] > 0:
            analysis["recommendations"].append(
                f"有 {stage_data['negotiating']['count']} 个机会在谈判阶段，重点关注促成成交"
            )
        
        return analysis
    
    async def analyze_lost_deals(
        self,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        分析丢单原因
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(Opportunity).where(
            and_(
                Opportunity.stage == "closed_lost",
                Opportunity.updated_at >= cutoff_date
            )
        )
        
        result = await self.db.execute(query)
        lost_opportunities = result.scalars().all()
        
        if not lost_opportunities:
            return {
                "total_lost": 0,
                "total_amount": 0,
                "analysis": "近期无丢单记录"
            }
        
        total_amount = sum(o.amount or 0 for o in lost_opportunities)
        
        reasons = {}
        for opp in lost_opportunities:
            reason = opp.remark or "未说明原因"
            reasons[reason] = reasons.get(reason, 0) + 1
        
        sorted_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)
        
        try:
            ai_analysis = await ai_service.analyze_lost_reason([
                {
                    "name": o.name,
                    "amount": o.amount,
                    "customer_name": o.customer_name,
                    "remark": o.remark
                }
                for o in lost_opportunities
            ])
        except Exception as e:
            logger.error(f"AI分析丢单原因失败: {e}")
            ai_analysis = {"improvement_suggestions": []}
        
        analysis = {
            "period_days": days,
            "total_lost": len(lost_opportunities),
            "total_amount": total_amount,
            "avg_lost_amount": total_amount / len(lost_opportunities),
            "reasons": [
                {"reason": r, "count": c, "percentage": c / len(lost_opportunities) * 100}
                for r, c in sorted_reasons
            ],
            "ai_analysis": ai_analysis,
            "recommendations": ai_analysis.get("improvement_suggestions", [])
        }
        
        return analysis
    
    async def analyze_sales_trend(
        self,
        months: int = 6
    ) -> Dict[str, Any]:
        """
        分析销售趋势
        """
        trends = []
        
        for i in range(months):
            month_start = datetime.now().replace(day=1) - timedelta(days=i*30)
            month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            
            won_query = select(
                func.count(Opportunity.id).label('count'),
                func.sum(Opportunity.amount).label('amount')
            ).where(
                and_(
                    Opportunity.stage == "closed_won",
                    Opportunity.updated_at >= month_start,
                    Opportunity.updated_at <= month_end
                )
            )
            
            won_result = await self.db.execute(won_query)
            won_row = won_result.one()
            
            new_customers_query = select(func.count(Customer.id)).where(
                and_(
                    Customer.created_at >= month_start,
                    Customer.created_at <= month_end
                )
            )
            
            new_customers_result = await self.db.execute(new_customers_query)
            new_customers = new_customers_result.scalar() or 0
            
            trends.append({
                "month": month_start.strftime("%Y-%m"),
                "won_count": won_row.count or 0,
                "won_amount": won_row.amount or 0,
                "new_customers": new_customers
            })
        
        trends.reverse()
        
        amounts = [t["won_amount"] for t in trends]
        if len(amounts) >= 2:
            if amounts[-1] > amounts[-2]:
                trend_direction = "上升"
                change_rate = (amounts[-1] - amounts[-2]) / amounts[-2] * 100 if amounts[-2] > 0 else 0
            elif amounts[-1] < amounts[-2]:
                trend_direction = "下降"
                change_rate = (amounts[-2] - amounts[-1]) / amounts[-2] * 100 if amounts[-2] > 0 else 0
            else:
                trend_direction = "持平"
                change_rate = 0
        else:
            trend_direction = "数据不足"
            change_rate = 0
        
        analysis = {
            "period_months": months,
            "trends": trends,
            "trend_direction": trend_direction,
            "change_rate": round(change_rate, 1),
            "total_won_amount": sum(t["won_amount"] for t in trends),
            "total_won_count": sum(t["won_count"] for t in trends),
            "total_new_customers": sum(t["new_customers"] for t in trends),
            "avg_monthly_amount": sum(t["won_amount"] for t in trends) / months
        }
        
        return analysis
    
    async def generate_sales_insights(self) -> Dict[str, Any]:
        """
        生成综合销售洞察
        """
        funnel_analysis = await self.analyze_sales_funnel()
        trend_analysis = await self.analyze_sales_trend()
        lost_analysis = await self.analyze_lost_deals()
        
        high_value_query = select(Customer).where(
            Customer.status.in_(["interested", "negotiating"])
        ).limit(10)
        high_value_result = await self.db.execute(high_value_query)
        high_value_customers = high_value_result.scalars().all()
        
        dashboard_data = {
            "funnel": {
                "total_opportunities": funnel_analysis["total_opportunities"],
                "total_amount": funnel_analysis["total_amount"],
                "conversion_rate": funnel_analysis["overall_conversion"]
            },
            "trend": {
                "direction": trend_analysis["trend_direction"],
                "change_rate": trend_analysis["change_rate"],
                "monthly_avg": trend_analysis["avg_monthly_amount"]
            },
            "lost": {
                "count": lost_analysis["total_lost"],
                "amount": lost_analysis["total_amount"]
            }
        }
        
        try:
            ai_insights = await ai_service.get_sales_insights(dashboard_data)
        except Exception as e:
            logger.error(f"AI洞察生成失败: {e}")
            ai_insights = {
                "summary": "数据加载完成",
                "highlights": [],
                "concerns": [],
                "recommendations": []
            }
        
        insights = {
            "generated_at": datetime.now(),
            "funnel_analysis": funnel_analysis,
            "trend_analysis": trend_analysis,
            "lost_analysis": lost_analysis,
            "ai_insights": ai_insights,
            "priority_actions": []
        }
        
        if funnel_analysis["bottlenecks"]:
            insights["priority_actions"].append({
                "priority": "high",
                "action": "优化销售漏斗瓶颈",
                "details": f"发现 {len(funnel_analysis['bottlenecks'])} 个转化瓶颈"
            })
        
        if trend_analysis["trend_direction"] == "下降":
            insights["priority_actions"].append({
                "priority": "high",
                "action": "扭转销售下滑趋势",
                "details": f"销售额下降 {trend_analysis['change_rate']}%"
            })
        
        if lost_analysis["total_lost"] > 3:
            insights["priority_actions"].append({
                "priority": "medium",
                "action": "降低丢单率",
                "details": f"近90天丢失 {lost_analysis['total_lost']} 个机会"
            })
        
        return insights
    
    async def analyze_opportunity_risk(
        self,
        opportunity_id: int
    ) -> Dict[str, Any]:
        """
        分析机会风险
        """
        query = select(Opportunity).where(Opportunity.id == opportunity_id)
        result = await self.db.execute(query)
        opportunity = result.scalar_one_or_none()
        
        if not opportunity:
            return {"error": "机会不存在"}
        
        risks = []
        risk_score = 0
        
        days_since_update = (datetime.now() - opportunity.updated_at).days
        if days_since_update > 7:
            risks.append({
                "type": "stagnation",
                "severity": "high" if days_since_update > 14 else "medium",
                "description": f"机会已 {days_since_update} 天无进展"
            })
            risk_score += 20
        
        if opportunity.probability and opportunity.probability < 0.3:
            risks.append({
                "type": "low_probability",
                "severity": "high",
                "description": f"成交概率较低 ({opportunity.probability*100:.0f}%)"
            })
            risk_score += 25
        
        if opportunity.expected_date:
            days_to_deadline = (opportunity.expected_date - datetime.now().date()).days
            if days_to_deadline < 0:
                risks.append({
                    "type": "overdue",
                    "severity": "high",
                    "description": f"已超过预期成交日期 {-days_to_deadline} 天"
                })
                risk_score += 30
            elif days_to_deadline < 7:
                risks.append({
                    "type": "deadline_approaching",
                    "severity": "medium",
                    "description": f"距离预期成交日期仅剩 {days_to_deadline} 天"
                })
                risk_score += 10
        
        if opportunity.amount and opportunity.amount > 100000:
            risks.append({
                "type": "high_value",
                "severity": "info",
                "description": "高价值机会，需要特别关注"
            })
        
        risk_level = "低"
        if risk_score >= 50:
            risk_level = "高"
        elif risk_score >= 25:
            risk_level = "中"
        
        return {
            "opportunity_id": opportunity_id,
            "opportunity_name": opportunity.name,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risks": risks,
            "recommendations": self._generate_risk_recommendations(risks)
        }
    
    def _generate_risk_recommendations(self, risks: List[Dict]) -> List[str]:
        """
        根据风险生成建议
        """
        recommendations = []
        
        for risk in risks:
            if risk["type"] == "stagnation":
                recommendations.append("建议立即联系客户，了解项目进展")
            elif risk["type"] == "low_probability":
                recommendations.append("建议分析竞争态势，制定差异化策略")
            elif risk["type"] == "overdue":
                recommendations.append("建议重新评估成交可能性，调整预期日期")
            elif risk["type"] == "deadline_approaching":
                recommendations.append("建议加速推进，争取在预期日期前成交")
            elif risk["type"] == "high_value":
                recommendations.append("高价值机会，建议安排高层参与")
        
        return recommendations
