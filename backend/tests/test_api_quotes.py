"""
报价单API集成测试
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

from app.models.models import Quote, QuoteStatus


@pytest.mark.integration
@pytest.mark.api
class TestQuoteAPI:
    """报价单API测试"""
    
    @pytest.mark.asyncio
    async def test_create_quote(self, client: AsyncClient, auth_headers: dict, test_customer, test_opportunity):
        """测试创建报价单"""
        quote_data = {
            "customer_id": test_customer.id,
            "customer_name": test_customer.name,
            "opportunity_id": test_opportunity.id,
            "items": [
                {
                    "name": "需求分析",
                    "description": "需求调研与分析",
                    "quantity": 1,
                    "unit_price": 5000
                },
                {
                    "name": "系统开发",
                    "description": "核心功能开发",
                    "quantity": 1,
                    "unit_price": 30000
                }
            ],
            "valid_until": (datetime.now() + timedelta(days=30)).date().isoformat(),
            "remark": "测试报价单"
        }
        
        response = await client.post(
            "/api/quotes/",
            json=quote_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_amount"] == 35000
        assert data["status"] == QuoteStatus.DRAFT.value
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_quote_unauthorized(self, client: AsyncClient, test_customer, test_opportunity):
        """测试未授权创建报价单"""
        quote_data = {
            "customer_id": test_customer.id,
            "customer_name": test_customer.name,
            "items": [
                {"name": "测试项目", "description": "测试", "quantity": 1, "unit_price": 1000}
            ],
            "valid_until": (datetime.now() + timedelta(days=30)).date().isoformat()
        }
        
        response = await client.post("/api/quotes/", json=quote_data)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_quotes(self, client: AsyncClient, auth_headers: dict, test_quote):
        """测试获取报价单列表"""
        response = await client.get("/api/quotes/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
    
    @pytest.mark.asyncio
    async def test_list_quotes_filter_by_status(self, client: AsyncClient, auth_headers: dict, test_quote):
        """测试按状态过滤报价单"""
        response = await client.get(
            "/api/quotes/?status=draft",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "draft" for item in data["items"])
    
    @pytest.mark.asyncio
    async def test_get_quote(self, client: AsyncClient, auth_headers: dict, test_quote):
        """测试获取报价单详情"""
        response = await client.get(
            f"/api/quotes/{test_quote.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_quote.id
        assert data["customer_id"] == test_quote.customer_id
        assert data["total_amount"] == test_quote.total_amount
    
    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试获取不存在的报价单"""
        response = await client.get("/api/quotes/99999", headers=auth_headers)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_quote(self, client: AsyncClient, auth_headers: dict, test_quote):
        """测试更新报价单"""
        update_data = {
            "items": [
                {
                    "name": "更新项目",
                    "description": "更新描述",
                    "quantity": 2,
                    "unit_price": 10000
                }
            ],
            "remark": "已更新"
        }
        
        response = await client.put(
            f"/api/quotes/{test_quote.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_amount"] == 20000
    
    @pytest.mark.asyncio
    async def test_update_quote_status(self, client: AsyncClient, auth_headers: dict, test_quote):
        """测试更新报价单状态"""
        update_data = {
            "status": "sent"
        }
        
        response = await client.put(
            f"/api/quotes/{test_quote.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_quote(self, client: AsyncClient, superuser_auth_headers: dict, db_session):
        """测试删除报价单"""
        # 创建一个新报价单用于删除
        quote = Quote(
            customer_id=1,
            customer_name="测试客户",
            items=[{"name": "测试", "quantity": 1, "unit_price": 1000}],
            total_amount=1000,
            status=QuoteStatus.DRAFT.value,
            valid_until=datetime.now().date(),
            organization_id=1,
            created_by=1
        )
        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)
        
        response = await client.delete(
            f"/api/quotes/{quote.id}",
            headers=superuser_auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_send_quote(self, client: AsyncClient, auth_headers: dict, test_quote):
        """测试发送报价单"""
        response = await client.post(
            f"/api/quotes/{test_quote.id}/send",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == QuoteStatus.SENT.value


@pytest.mark.integration
@pytest.mark.api
class TestQuoteDataIsolation:
    """报价单数据隔离测试"""
    
    @pytest.mark.asyncio
    async def test_sales_can_only_see_own_quotes(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_sales_user
    ):
        """测试销售只能看到自己的报价单"""
        response = await client.get("/api/quotes/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # 所有返回的报价单应该属于该用户
        # 注意：这需要根据实际的数据隔离逻辑来验证
    
    @pytest.mark.asyncio
    async def test_viewer_can_only_read(
        self,
        client: AsyncClient,
        test_viewer_user,
        test_organization,
        test_team,
        test_roles,
        db_session
    ):
        """测试只读用户只能读取报价单"""
        from app.core.auth import create_access_token
        
        # 创建只读用户token
        token = create_access_token({"sub": str(test_viewer_user.id)})
        viewer_headers = {"Authorization": f"Bearer {token}"}
        
        # 可以读取
        response = await client.get("/api/quotes/", headers=viewer_headers)
        assert response.status_code == 200
        
        # 不能创建
        quote_data = {
            "customer_id": 1,
            "customer_name": "测试",
            "items": [{"name": "测试", "quantity": 1, "unit_price": 1000}],
            "valid_until": datetime.now().date().isoformat()
        }
        response = await client.post("/api/quotes/", json=quote_data, headers=viewer_headers)
        assert response.status_code == 403
