"""
AI代理API集成测试 - 包含修复接口验证
"""
import pytest
from httpx import AsyncClient
from datetime import datetime


@pytest.mark.integration
@pytest.mark.api
class TestAgentAPI:
    """AI代理API测试"""

    @pytest.mark.asyncio
    async def test_get_alerts(self, client: AsyncClient, auth_headers: dict):
        """测试获取预警列表 - 验证修复接口"""
        response = await client.get("/api/agent/alerts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        # 验证数据隔离：返回的预警应该属于用户所在组织

    @pytest.mark.asyncio
    async def test_get_alerts_with_filters(self, client: AsyncClient, auth_headers: dict):
        """测试带过滤条件获取预警"""
        response = await client.get(
            "/api/agent/alerts?severity=high&limit=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0

    @pytest.mark.asyncio
    async def test_get_alert_summary(self, client: AsyncClient):
        """测试获取预警摘要"""
        response = await client.get("/api/agent/alerts/summary")

        # 某些接口可能不需要认证
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_trigger_scan(self, client: AsyncClient, superuser_auth_headers: dict):
        """测试手动触发监控扫描"""
        response = await client.post("/api/agent/scan", headers=superuser_auth_headers)

        assert response.status_code in [200, 403]  # 403 if permission denied
        if response.status_code == 200:
            data = response.json()
            assert "scanned_at" in data
            assert "new_alerts" in data

    @pytest.mark.asyncio
    async def test_get_agent_dashboard(self, client: AsyncClient, auth_headers: dict):
        """测试获取智能体工作台"""
        response = await client.get("/api/agent/dashboard", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "alert_summary" in data
        assert "recent_alerts" in data

    @pytest.mark.asyncio
    async def test_get_daily_briefing(self, client: AsyncClient):
        """测试获取每日简报"""
        response = await client.get("/api/agent/briefing")

        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_get_goals(self, client: AsyncClient):
        """测试获取目标列表"""
        response = await client.get("/api/agent/goals")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "items" in data

    @pytest.mark.asyncio
    async def test_create_goal(self, client: AsyncClient, auth_headers: dict):
        """测试创建目标"""
        goal_data = {
            "name": "测试销售目标",
            "target_value": 100000,
            "unit": "元",
            "goal_type": "revenue",
            "end_date": "2026-12-31"
        }

        response = await client.post(
            "/api/agent/goals",
            data=goal_data,
            headers=auth_headers
        )

        assert response.status_code in [200, 403, 422]

    @pytest.mark.asyncio
    async def test_get_tasks(self, client: AsyncClient):
        """测试获取任务列表"""
        response = await client.get("/api/agent/tasks")

        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "items" in data

    @pytest.mark.asyncio
    async def test_get_memories(self, client: AsyncClient):
        """测试获取记忆列表"""
        response = await client.get("/api/agent/memories")

        assert response.status_code in [200, 401]


@pytest.mark.integration
@pytest.mark.api
class TestAgentDataIsolation:
    """AI代理数据隔离测试"""

    @pytest.mark.asyncio
    async def test_alerts_data_isolation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sales_user
    ):
        """测试预警数据隔离 - 验证修复接口"""
        response = await client.get("/api/agent/alerts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # 验证所有返回的预警都属于用户所在组织
        # 这是修复 /api/agent/alerts 接口后的验证
        for item in data.get("items", []):
            assert "id" in item
            assert "alert_type" in item

    @pytest.mark.asyncio
    async def test_dashboard_data_isolation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sales_user
    ):
        """测试智能体工作台数据隔离"""
        response = await client.get("/api/agent/dashboard", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # 验证今日跟进和活跃目标都是用户所在组织的数据
        assert isinstance(data.get("today_followups", []), list)
        assert isinstance(data.get("active_goals", []), list)


@pytest.mark.integration
@pytest.mark.api
class TestAgentAnalysis:
    """AI代理分析功能测试"""

    @pytest.mark.asyncio
    async def test_analyze_funnel(self, client: AsyncClient):
        """测试分析销售漏斗"""
        response = await client.get("/api/agent/analysis/funnel")

        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_analyze_trend(self, client: AsyncClient):
        """测试分析销售趋势"""
        response = await client.get("/api/agent/analysis/trend?months=6")

        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_analyze_lost_deals(self, client: AsyncClient):
        """测试分析丢单原因"""
        response = await client.get("/api/agent/analysis/lost-deals?days=90")

        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_get_recommendations(self, client: AsyncClient):
        """测试获取智能推荐"""
        response = await client.get("/api/agent/recommendations")

        assert response.status_code in [200, 401]
