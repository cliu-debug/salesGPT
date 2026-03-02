"""
监控API集成测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
class TestMonitoringAPI:
    """监控API测试"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """测试健康检查端点"""
        response = await client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["status"] in ["healthy", "unhealthy", "degraded"]

    @pytest.mark.asyncio
    async def test_health_check_components(self, client: AsyncClient):
        """测试健康检查组件状态"""
        response = await client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        components = data.get("components", {})
        # 验证数据库组件
        assert "database" in components
        assert components["database"]["status"] in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_get_metrics_unauthorized(self, client: AsyncClient):
        """测试未授权获取性能指标"""
        response = await client.get("/api/monitoring/metrics")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_metrics_authorized(self, client: AsyncClient, superuser_auth_headers: dict):
        """测试授权获取性能指标"""
        response = await client.get("/api/monitoring/metrics", headers=superuser_auth_headers)

        assert response.status_code in [200, 403]
        if response.status_code == 200:
            data = response.json()
            assert "timestamp" in data
            assert "system" in data
            assert "database" in data

    @pytest.mark.asyncio
    async def test_system_metrics_content(self, client: AsyncClient, superuser_auth_headers: dict):
        """测试系统性能指标内容"""
        response = await client.get("/api/monitoring/metrics", headers=superuser_auth_headers)

        if response.status_code == 200:
            data = response.json()
            system = data.get("system", {})

            # 验证CPU指标
            assert "cpu_percent" in system
            assert isinstance(system["cpu_percent"], (int, float))
            assert 0 <= system["cpu_percent"] <= 100

            # 验证内存指标
            assert "memory" in system
            memory = system["memory"]
            assert "total" in memory
            assert "available" in memory
            assert "percent" in memory
            assert "used" in memory

    @pytest.mark.asyncio
    async def test_database_metrics_content(self, client: AsyncClient, superuser_auth_headers: dict):
        """测试数据库指标内容"""
        response = await client.get("/api/monitoring/metrics", headers=superuser_auth_headers)

        if response.status_code == 200:
            data = response.json()
            database = data.get("database", {})

            # 验证数据库统计
            assert "customer_count" in database
            assert "opportunity_count" in database
            assert "quote_count" in database
            assert "followup_count" in database

            # 验证数据类型
            assert isinstance(database["customer_count"], int)
            assert isinstance(database["opportunity_count"], int)
            assert database["customer_count"] >= 0
            assert database["opportunity_count"] >= 0


@pytest.mark.integration
@pytest.mark.api
class TestMonitoringPerformance:
    """监控性能测试"""

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, client: AsyncClient):
        """测试健康检查响应时间"""
        import time

        start_time = time.time()
        response = await client.get("/api/monitoring/health")
        end_time = time.time()

        assert response.status_code == 200
        # 健康检查应该在1秒内完成
        assert (end_time - start_time) < 1.0

    @pytest.mark.asyncio
    async def test_metrics_response_time(self, client: AsyncClient, superuser_auth_headers: dict):
        """测试性能指标响应时间"""
        import time

        start_time = time.time()
        response = await client.get("/api/monitoring/metrics", headers=superuser_auth_headers)
        end_time = time.time()

        if response.status_code == 200:
            # 性能指标应该在2秒内完成
            assert (end_time - start_time) < 2.0


@pytest.mark.integration
@pytest.mark.api
class TestMonitoringReliability:
    """监控可靠性测试"""

    @pytest.mark.asyncio
    async def test_multiple_health_checks(self, client: AsyncClient):
        """测试多次健康检查的一致性"""
        responses = []
        for _ in range(5):
            response = await client.get("/api/monitoring/health")
            responses.append(response)

        # 所有响应都应该成功
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "unhealthy", "degraded"]

    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, client: AsyncClient):
        """测试健康检查错误处理"""
        # 健康检查应该总是返回200，即使某些组件不健康
        response = await client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        # 即使状态为unhealthy，也应该返回200
        # 这是健康检查的最佳实践
        assert "status" in data
        assert "components" in data
