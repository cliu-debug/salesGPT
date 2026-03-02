"""
权限模块单元测试
"""
import pytest

from app.core.permissions import (
    PermissionChecker, DEFAULT_PERMISSIONS,
    check_user_permission, get_permission_list
)


class TestPermissionChecker:
    """权限检查器测试"""
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_has_permission_super_admin(self):
        """测试超级管理员权限"""
        # 超级管理员应该拥有所有权限
        assert PermissionChecker.has_permission("super_admin", "customer:read") is True
        assert PermissionChecker.has_permission("super_admin", "customer:write") is True
        assert PermissionChecker.has_permission("super_admin", "user:delete") is True
        assert PermissionChecker.has_permission("super_admin", "anything:any") is True
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_has_permission_admin(self):
        """测试管理员权限"""
        # 管理员应该有customer:*权限
        assert PermissionChecker.has_permission("admin", "customer:read") is True
        assert PermissionChecker.has_permission("admin", "customer:write") is True
        assert PermissionChecker.has_permission("admin", "customer:delete") is True
        
        # 管理员应该有用户读取权限
        assert PermissionChecker.has_permission("admin", "user:read") is True
        
        # 管理员没有删除用户的权限（根据DEFAULT_PERMISSIONS定义）
        assert PermissionChecker.has_permission("admin", "user:delete") is False
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_has_permission_manager(self):
        """测试经理权限"""
        # 经理应该有客户读写权限
        assert PermissionChecker.has_permission("manager", "customer:read") is True
        assert PermissionChecker.has_permission("manager", "customer:write") is True
        
        # 经理有删除客户的权限（可以删除自己团队的数据）
        assert PermissionChecker.has_permission("manager", "customer:delete") is True
        
        # 经理有报表读取权限
        assert PermissionChecker.has_permission("manager", "report:read") is True
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_has_permission_sales(self):
        """测试销售人员权限"""
        # 销售有客户读写权限
        assert PermissionChecker.has_permission("sales", "customer:read") is True
        assert PermissionChecker.has_permission("sales", "customer:write") is True
        
        # 销售没有用户管理权限
        assert PermissionChecker.has_permission("sales", "user:read") is False
        assert PermissionChecker.has_permission("sales", "user:write") is False
        
        # 销售没有团队管理权限
        assert PermissionChecker.has_permission("sales", "team:read") is False
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_has_permission_viewer(self):
        """测试只读用户权限"""
        # 只读用户只有读取权限
        assert PermissionChecker.has_permission("viewer", "customer:read") is True
        assert PermissionChecker.has_permission("viewer", "opportunity:read") is True
        
        # 只读用户没有写权限
        assert PermissionChecker.has_permission("viewer", "customer:write") is False
        assert PermissionChecker.has_permission("viewer", "opportunity:write") is False
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_has_permission_invalid_role(self):
        """测试无效角色"""
        # 无效角色应该没有权限
        assert PermissionChecker.has_permission("invalid_role", "customer:read") is False
        assert PermissionChecker.has_permission("", "customer:read") is False
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_wildcard_permission_matching(self):
        """测试通配符权限匹配"""
        # customer:* 应该匹配 customer:read
        assert PermissionChecker.has_permission("admin", "customer:read") is True
        assert PermissionChecker.has_permission("admin", "customer:write") is True
        
        # agent:* 应该匹配所有agent相关权限
        assert PermissionChecker.has_permission("manager", "agent:read") is True
        assert PermissionChecker.has_permission("manager", "agent:write") is True


class TestDefaultPermissions:
    """默认权限测试"""
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_default_permissions_structure(self):
        """测试默认权限结构"""
        assert "super_admin" in DEFAULT_PERMISSIONS
        assert "admin" in DEFAULT_PERMISSIONS
        assert "manager" in DEFAULT_PERMISSIONS
        assert "sales" in DEFAULT_PERMISSIONS
        assert "viewer" in DEFAULT_PERMISSIONS
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_super_admin_has_all_permission(self):
        """测试超级管理员有全部权限"""
        assert "*" in DEFAULT_PERMISSIONS["super_admin"]
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_get_permission_list(self):
        """测试获取权限列表"""
        permissions = get_permission_list()
        
        assert permissions == DEFAULT_PERMISSIONS
        assert isinstance(permissions, dict)
        assert len(permissions) > 0


class TestCheckUserPermission:
    """用户权限检查测试"""
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_check_permission_superuser(self, test_superuser):
        """测试超级管理员权限检查"""
        # 模拟用户对象
        has_permission = PermissionChecker.check_permission(
            test_superuser, "any:permission"
        )
        assert has_permission is True
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_check_permission_admin(self, test_admin_user):
        """测试管理员权限检查"""
        has_permission = PermissionChecker.check_permission(
            test_admin_user, "customer:read"
        )
        assert has_permission is True
        
        has_permission = PermissionChecker.check_permission(
            test_admin_user, "user:delete"
        )
        assert has_permission is False
    
    @pytest.mark.unit
    @pytest.mark.permission
    def test_check_permission_sales(self, test_sales_user):
        """测试销售权限检查"""
        has_permission = PermissionChecker.check_permission(
            test_sales_user, "customer:read"
        )
        assert has_permission is True
        
        has_permission = PermissionChecker.check_permission(
            test_sales_user, "team:read"
        )
        assert has_permission is False
