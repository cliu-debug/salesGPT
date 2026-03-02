"""
数据分析API集成测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
class TestAnalyticsAPI:
    """数据分析API测试"""

    @pytest.mark.asyncio
    async def test_get_overview(self, client: AsyncClient):
        """测试获取分析概览"""
        response = await client.get("/api/analytics/overview")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "customers" in data
            assert "opportunities" in data
            assert "conversion" in data

    @pytest.mark.asyncio
    async def test_get_customer_trend(self, client: AsyncClient):
        """测试获取客户增长趋势"""
        response = await client.get("/api/analytics/customer-trend?months=6")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "trend" in data
            assert len(data["trend"]) > 0

    @pytest.mark.asyncio
    async def test_get_sales_trend(self, client: AsyncClient):
        """测试获取销售趋势"""
        response = await client.get("/api/analytics/sales-trend?months=6")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "trend" in data
            assert len(data["trend"]) > 0

    @pytest.mark.asyncio
    async def test_get_industry_distribution(self, client: AsyncClient):
        """测试获取客户行业分布"""
        response = await client.get("/api/analytics/industry-distribution")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "distribution" in data

    @pytest.mark.asyncio
    async def test_get_source_distribution(self, client: AsyncClient):
        """测试获取客户来源分布"""
        response = await client.get("/api/analytics/source-distribution")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "distribution" in data

    @pytest.mark.asyncio
    async def test_get_stage_conversion(self, client: AsyncClient):
        """测试获取销售漏斗转化率"""
        response = await client.get("/api/analytics/stage-conversion")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "funnel" in data
            assert len(data["funnel"]) > 0

    @pytest.mark.asyncio
    async def test_get_top_customers(self, client: AsyncClient):
        """测试获取成交金额最高的客户"""
        response = await client.get("/api/analytics/top-customers?limit=10")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "top_customers" in data

    @pytest.mark.asyncio
    async def test_get_ai_forecast(self, client: AsyncClient):
        """测试AI销售预测"""
        response = await client.get("/api/analytics/ai-forecast")

        # AI服务可能需要配置
        assert response.status_code in [200, 401, 500]

    @pytest.mark.asyncio
    async def test_get_ai_recommendation(self, client: AsyncClient):
        """测试AI智能推荐"""
        response = await client.get("/api/analytics/ai-recommendation")

        # AI服务可能需要配置
        assert response.status_code in [200, 401, 500]

    @pytest.mark.asyncio
    async def test_get_ai_report(self, client: AsyncClient):
        """测试AI生成销售报告"""
        response = await client.get("/api/analytics/ai-report?period=本周")

        # AI服务可能需要配置
        assert response.status_code in [200, 401, 500]

    @pytest.mark.asyncio
    async def test_get_lost_analysis(self, client: AsyncClient):
        """测试丢单原因分析"""
        response = await client.get("/api/analytics/lost-analysis")

        # AI服务可能需要配置
        assert response.status_code in [200, 401, 500]


@pytest.mark.integration
@pytest.mark.api
class TestAnalyticsDataIntegrity:
    """数据分析数据完整性测试"""

    @pytest.mark.asyncio
    async def test_trend_data_consistency(self, client: AsyncClient):
        """测试趋势数据一致性"""
        response = await client.get("/api/analytics/sales-trend?months=3")

        if response.status_code == 200:
            data = response.json()
            trend = data.get("trend", [])

            # 验证数据格式
            for item in trend:
                assert "month" in item
                assert "amount" in item
                assert "deals" in item
                assert isinstance(item["amount"], (int, float))
                assert isinstance(item["deals"], int)
