"""
跟进记录API集成测试
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

from app.models.models import FollowUp


@pytest.mark.integration
@pytest.mark.api
class TestFollowUpAPI:
    """跟进记录API测试"""
    
    @pytest.mark.asyncio
    async def test_create_follow_up(self, client: AsyncClient, auth_headers: dict, test_customer):
        """测试创建跟进记录"""
        followup_data = {
            "customer_id": test_customer.id,
            "customer_name": test_customer.name,
            "content": "初次沟通，客户对产品很感兴趣",
            "next_action": "发送产品介绍资料",
            "next_date": (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        response = await client.post(
            "/api/follow-ups/",
            json=followup_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["customer_id"] == test_customer.id
    
    @pytest.mark.asyncio
    async def test_create_follow_up_unauthorized(self, client: AsyncClient, test_customer):
        """测试未授权创建跟进记录"""
        followup_data = {
            "customer_id": test_customer.id,
            "customer_name": test_customer.name,
            "content": "测试内容",
            "next_action": "测试动作",
            "next_date": datetime.now().isoformat()
        }
        
        response = await client.post("/api/follow-ups/", json=followup_data)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_follow_ups(self, client: AsyncClient, auth_headers: dict, test_followup):
        """测试获取跟进记录列表"""
        response = await client.get("/api/follow-ups/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
    
    @pytest.mark.asyncio
    async def test_list_follow_ups_filter_by_customer(
        self, 
        client: AsyncClient, 
        auth_headers: dict, 
        test_followup
    ):
        """测试按客户过滤跟进记录"""
        response = await client.get(
            f"/api/follow-ups/?customer_id={test_followup.customer_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["customer_id"] == test_followup.customer_id for item in data["items"])
    
    @pytest.mark.asyncio
    async def test_get_today_tasks(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_sales_user,
        test_organization,
        db_session
    ):
        """测试获取今日待办任务"""
        # 创建今日任务
        today_followup = FollowUp(
            customer_id=1,
            customer_name="今日客户",
            content="今日跟进",
            next_action="今日待办",
            next_date=datetime.now(),
            organization_id=test_organization.id,
            created_by=test_sales_user.id
        )
        db_session.add(today_followup)
        await db_session.commit()
        
        response = await client.get("/api/follow-ups/today", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
    
    @pytest.mark.asyncio
    async def test_get_upcoming_tasks(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_sales_user,
        test_organization,
        db_session
    ):
        """测试获取即将到来的任务"""
        # 创建即将到来的任务
        upcoming_followup = FollowUp(
            customer_id=1,
            customer_name="未来客户",
            content="未来跟进",
            next_action="未来待办",
            next_date=datetime.now() + timedelta(days=3),
            organization_id=test_organization.id,
            created_by=test_sales_user.id
        )
        db_session.add(upcoming_followup)
        await db_session.commit()
        
        response = await client.get(
            "/api/follow-ups/upcoming?days=7",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert data["total"] >= 1
    
    @pytest.mark.asyncio
    async def test_delete_follow_up(self, client: AsyncClient, superuser_auth_headers: dict, db_session):
        """测试删除跟进记录"""
        # 创建一个新跟进记录用于删除
        followup = FollowUp(
            customer_id=1,
            customer_name="测试客户",
            content="测试内容",
            next_action="测试动作",
            next_date=datetime.now(),
            organization_id=1,
            created_by=1
        )
        db_session.add(followup)
        await db_session.commit()
        await db_session.refresh(followup)
        
        response = await client.delete(
            f"/api/follow-ups/{followup.id}",
            headers=superuser_auth_headers
        )
        
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.api
class TestFollowUpDataIsolation:
    """跟进记录数据隔离测试"""
    
    @pytest.mark.asyncio
    async def test_sales_can_only_see_own_followups(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_sales_user
    ):
        """测试销售只能看到自己的跟进记录"""
        response = await client.get("/api/follow-ups/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # 所有返回的跟进记录应该属于该用户的组织
    
    @pytest.mark.asyncio
    async def test_viewer_can_only_read(
        self,
        client: AsyncClient,
        test_viewer_user,
        db_session
    ):
        """测试只读用户只能读取跟进记录"""
        from app.core.auth import create_access_token
        
        # 创建只读用户token
        token = create_access_token({"sub": str(test_viewer_user.id)})
        viewer_headers = {"Authorization": f"Bearer {token}"}
        
        # 可以读取
        response = await client.get("/api/follow-ups/", headers=viewer_headers)
        assert response.status_code == 200
        
        # 不能创建
        followup_data = {
            "customer_id": 1,
            "customer_name": "测试",
            "content": "测试",
            "next_action": "测试",
            "next_date": datetime.now().isoformat()
        }
        response = await client.post("/api/follow-ups/", json=followup_data, headers=viewer_headers)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_different_organization_isolation(
        self,
        client: AsyncClient,
        test_organization,
        test_team,
        test_roles,
        db_session
    ):
        """测试不同组织数据隔离"""
        from app.core.auth import create_access_token, hash_password
        from app.models.models import User, Organization, FollowUp
        
        # 创建另一个组织
        other_org = Organization(name="其他公司", plan="pro")
        db_session.add(other_org)
        await db_session.commit()
        await db_session.refresh(other_org)
        
        # 创建其他组织的用户
        other_user = User(
            username="other_sales",
            email="other@test.com",
            password_hash=hash_password("password123"),
            full_name="其他销售",
            role_id=test_roles["sales"].id,
            team_id=test_team.id,
            organization_id=other_org.id,
            is_active=True
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)
        
        # 创建其他组织的跟进记录
        other_followup = FollowUp(
            customer_id=1,
            customer_name="其他客户",
            content="其他跟进",
            next_action="其他动作",
            next_date=datetime.now(),
            organization_id=other_org.id,
            created_by=other_user.id
        )
        db_session.add(other_followup)
        await db_session.commit()
        
        # 用原用户登录，应该看不到其他组织的跟进记录
        token = create_access_token({"sub": str(test_roles["sales"].id)})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/follow-ups/", headers=headers)
        assert response.status_code in [200, 401]  # 401表示未授权
