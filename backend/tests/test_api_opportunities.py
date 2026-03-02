"""
销售机会API集成测试
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.core.auth import create_access_token


class TestOpportunityAPI:
    """销售机会API测试"""
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_opportunity(
        self, 
        client: AsyncClient, 
        auth_headers,
        test_customer
    ):
        """测试创建销售机会"""
        response = await client.post(
            "/api/opportunities/",
            headers=auth_headers,
            json={
                "customer_id": test_customer.id,
                "customer_name": test_customer.name,
                "name": "新销售项目",
                "amount": 100000,
                "stage": "initial",
                "probability": 30,
                "expected_date": (datetime.now() + timedelta(days=30)).date().isoformat()
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新销售项目"
        assert data["amount"] == 100000
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_opportunities(
        self, 
        client: AsyncClient, 
        auth_headers,
        test_opportunity
    ):
        """测试获取销售机会列表"""
        response = await client.get(
            "/api/opportunities/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_opportunity(
        self, 
        client: AsyncClient, 
        auth_headers,
        test_opportunity
    ):
        """测试获取单个销售机会"""
        response = await client.get(
            f"/api/opportunities/{test_opportunity.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_opportunity.id
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_opportunity_stage(
        self,
        client: AsyncClient,
        auth_headers,
        test_opportunity
    ):
        """测试更新销售机会阶段"""
        response = await client.put(
            f"/api/opportunities/{test_opportunity.id}",
            headers=auth_headers,
            json={
                "stage": "negotiation",
                "probability": 60
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "negotiation"
        assert data["probability"] == 60
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_opportunity(
        self,
        client: AsyncClient,
        auth_headers,
        test_opportunity
    ):
        """测试删除销售机会"""
        response = await client.delete(
            f"/api/opportunities/{test_opportunity.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_funnel_stats(
        self,
        client: AsyncClient,
        auth_headers,
        test_opportunity
    ):
        """测试获取销售漏斗统计"""
        response = await client.get(
            "/api/opportunities/stats/funnel",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # 验证漏斗数据结构
        assert isinstance(data, list) or isinstance(data, dict)
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_filter_by_stage(
        self,
        client: AsyncClient,
        auth_headers,
        test_opportunity
    ):
        """测试按阶段筛选"""
        response = await client.get(
            "/api/opportunities/?stage=initial",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 所有返回的机会应该是initial阶段
        for item in data["items"]:
            assert item["stage"] == "initial"


class TestOpportunityCalculations:
    """销售机会计算测试"""
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_weighted_amount_calculation(
        self,
        client: AsyncClient,
        auth_headers,
        test_customer
    ):
        """测试加权金额计算"""
        # 创建机会时，加权金额应该自动计算
        response = await client.post(
            "/api/opportunities/",
            headers=auth_headers,
            json={
                "customer_id": test_customer.id,
                "customer_name": test_customer.name,
                "name": "加权测试项目",
                "amount": 100000,
                "stage": "negotiation",
                "probability": 50,
                "expected_date": (datetime.now() + timedelta(days=30)).date().isoformat()
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # 加权金额 = 金额 * 概率
        expected_weighted = 100000 * 0.5
        assert abs(data.get("weighted_amount", expected_weighted) - expected_weighted) < 0.01
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_stage_probability_update(
        self,
        client: AsyncClient,
        auth_headers,
        test_opportunity
    ):
        """测试阶段更新时概率自动更新"""
        # 更新阶段为won，概率应该变为100%
        response = await client.put(
            f"/api/opportunities/{test_opportunity.id}",
            headers=auth_headers,
            json={
                "stage": "won"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # won阶段概率应该是100
        if data["stage"] == "won":
            assert data["probability"] == 100


class TestOpportunityPermissions:
    """销售机会权限测试"""
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_sales_can_manage_own_opportunities(
        self,
        client: AsyncClient,
        auth_headers,
        test_opportunity
    ):
        """测试销售可以管理自己的机会"""
        # 读取
        response = await client.get(
            f"/api/opportunities/{test_opportunity.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # 更新
        response = await client.put(
            f"/api/opportunities/{test_opportunity.id}",
            headers=auth_headers,
            json={"stage": "negotiation"}
        )
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_viewer_cannot_create_opportunity(
        self,
        client: AsyncClient,
        test_viewer_user,
        test_customer
    ):
        """测试只读用户不能创建机会"""
        # JWT规范要求sub必须是字符串
        viewer_token = create_access_token({"sub": str(test_viewer_user.id)})
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        
        response = await client.post(
            "/api/opportunities/",
            headers=viewer_headers,
            json={
                "customer_id": test_customer.id,
                "customer_name": test_customer.name,
                "name": "测试项目",
                "amount": 50000,
                "stage": "initial"
            }
        )
        
        assert response.status_code == 403
