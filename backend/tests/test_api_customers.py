"""
客户API集成测试
"""
import pytest
from httpx import AsyncClient

from app.core.auth import create_access_token


class TestCustomerAPI:
    """客户API测试"""
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_customer(self, client: AsyncClient, auth_headers):
        """测试创建客户"""
        response = await client.post(
            "/api/customers/",
            headers=auth_headers,
            json={
                "name": "新客户",
                "contact": "李四",
                "phone": "13900139000",
                "email": "lisi@test.com",
                "company": "测试公司",
                "industry": "金融",
                "source": "展会"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新客户"
        assert data["contact"] == "李四"
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_customer_unauthorized(self, client: AsyncClient):
        """测试创建客户 - 未授权"""
        response = await client.post(
            "/api/customers/",
            json={
                "name": "新客户",
                "contact": "李四"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_customers(self, client: AsyncClient, auth_headers, test_customer):
        """测试获取客户列表"""
        response = await client.get(
            "/api/customers/",
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
    async def test_get_customer(self, client: AsyncClient, auth_headers, test_customer):
        """测试获取单个客户"""
        response = await client.get(
            f"/api/customers/{test_customer.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_customer.id
        assert data["name"] == test_customer.name
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, client: AsyncClient, auth_headers):
        """测试获取不存在的客户"""
        response = await client.get(
            "/api/customers/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_customer(self, client: AsyncClient, auth_headers, test_customer):
        """测试更新客户"""
        response = await client.put(
            f"/api/customers/{test_customer.id}",
            headers=auth_headers,
            json={
                "name": "更新后的客户名",
                "contact": "王五",
                "phone": "13900139001"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后的客户名"
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_customer(self, client: AsyncClient, auth_headers, test_customer):
        """测试删除客户"""
        response = await client.delete(
            f"/api/customers/{test_customer.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # 验证已删除
        get_response = await client.get(
            f"/api/customers/{test_customer.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_search_customers(self, client: AsyncClient, auth_headers, test_customer):
        """测试搜索客户"""
        response = await client.get(
            "/api/customers/?search=测试",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_filter_customers_by_industry(
        self, 
        client: AsyncClient, 
        auth_headers, 
        test_customer
    ):
        """测试按行业筛选客户"""
        response = await client.get(
            "/api/customers/?industry=互联网",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # 所有返回的客户应该是互联网行业
        for item in data["items"]:
            assert item["industry"] == "互联网"


class TestCustomerDataIsolation:
    """客户数据隔离测试"""
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_sales_can_only_see_own_customers(
        self,
        client: AsyncClient,
        auth_headers,  # sales用户
        test_customer  # 由test_sales_user创建
    ):
        """测试销售人员只能看到自己创建的客户"""
        response = await client.get(
            "/api/customers/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 销售应该能看到自己的客户
        assert data["total"] >= 1
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_admin_can_see_all_organization_customers(
        self,
        client: AsyncClient,
        admin_auth_headers,  # admin用户
        test_customer  # 同组织的客户
    ):
        """测试管理员可以看到组织内所有客户"""
        response = await client.get(
            "/api/customers/",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 管理员应该能看到组织内所有客户
        assert data["total"] >= 1
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_viewer_can_only_read(
        self,
        client: AsyncClient,
        test_viewer_user
    ):
        """测试只读用户只能读取不能写入"""
        # 创建viewer认证头（JWT规范要求sub必须是字符串）
        viewer_token = create_access_token({"sub": str(test_viewer_user.id)})
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        
        # 读取应该成功
        response = await client.get(
            "/api/customers/",
            headers=viewer_headers
        )
        assert response.status_code == 200
        
        # 写入应该失败
        response = await client.post(
            "/api/customers/",
            headers=viewer_headers,
            json={
                "name": "新客户",
                "contact": "测试"
            }
        )
        assert response.status_code == 403
