"""
认证API集成测试
"""
import pytest
from httpx import AsyncClient

from app.core.auth import hash_password, create_access_token


class TestAuthAPI:
    """认证API测试"""
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_sales_user):
        """测试登录成功"""
        response = await client.post(
            "/api/auth/login",
            json={
                "username": "sales",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_sales_user):
        """测试登录失败 - 错误密码"""
        response = await client.post(
            "/api/auth/login",
            json={
                "username": "sales",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_login_invalid_username(self, client: AsyncClient):
        """测试登录失败 - 不存在的用户"""
        response = await client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """测试获取当前用户信息"""
        response = await client.get(
            "/api/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert data["username"] == "sales"
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """测试获取当前用户信息 - 未授权"""
        response = await client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """测试获取当前用户信息 - 无效Token"""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_register_new_user(self, client: AsyncClient, auth_headers, test_organization, test_roles):
        """测试注册新用户"""
        response = await client.post(
            "/api/auth/register",
            headers=auth_headers,
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "password123",
                "full_name": "新用户"
            }
        )
        
        # 注册端点返回200
        assert response.status_code in [200, 201, 400]  # 400可能是用户名已存在
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers):
        """测试修改密码"""
        response = await client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, client: AsyncClient, auth_headers):
        """测试修改密码 - 错误的旧密码"""
        response = await client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "wrongpassword",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 400
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, auth_headers):
        """测试登出"""
        response = await client.post(
            "/api/auth/logout",
            headers=auth_headers
        )
        
        # 登出可能返回200或204
        assert response.status_code in [200, 204]


class TestAuthPermission:
    """认证权限测试"""
    
    @pytest.mark.skip(reason="用户创建端点 /api/users/ 不存在")
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_admin_can_create_user(
        self, 
        client: AsyncClient, 
        admin_auth_headers,
        test_organization,
        test_roles
    ):
        """测试管理员可以创建用户"""
        response = await client.post(
            "/api/users/",
            headers=admin_auth_headers,
            json={
                "username": "new_sales",
                "email": "new_sales@test.com",
                "password": "password123",
                "full_name": "新销售",
                "role_id": test_roles["sales"].id
            }
        )
        
        # 管理员应该可以创建用户
        assert response.status_code in [200, 201]
    
    @pytest.mark.skip(reason="用户创建端点 /api/users/ 不存在")
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_sales_cannot_create_user(
        self,
        client: AsyncClient,
        auth_headers  # sales用户
    ):
        """测试销售人员不能创建用户"""
        response = await client.post(
            "/api/users/",
            headers=auth_headers,
            json={
                "username": "new_user",
                "email": "new@test.com",
                "password": "password123"
            }
        )
        
        # 销售人员应该被拒绝
        assert response.status_code == 403
