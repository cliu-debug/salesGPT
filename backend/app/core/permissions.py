"""
权限管理模块 - RBAC权限检查、数据隔离
"""
from typing import List, Optional, Callable
from functools import wraps
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import User
from app.core.auth import get_current_user
from app.core.database import get_db


# 默认权限定义
DEFAULT_PERMISSIONS = {
    "super_admin": [
        # 超级管理员拥有所有权限
        "*"
    ],
    "admin": [
        # 组织管理员
        "customer:*", "opportunity:*", "quote:*", "followup:*",
        "user:read", "user:write",
        "team:read", "team:write",
        "report:*", "analytics:*", "agent:*",
        "dashboard:*", "import-export:*", "monitoring:*"
    ],
    "manager": [
        # 团队经理
        "customer:read", "customer:write", "customer:delete",
        "opportunity:read", "opportunity:write", "opportunity:delete",
        "quote:read", "quote:write", "quote:delete",
        "followup:read", "followup:write",
        "user:read",
        "report:read", "analytics:read", "agent:*",
        "dashboard:read", "import-export:read", "monitoring:read"
    ],
    "sales": [
        # 销售人员
        "customer:read", "customer:write", "customer:delete",
        "opportunity:read", "opportunity:write", "opportunity:delete",
        "quote:read", "quote:write", "quote:delete",
        "followup:read", "followup:write",
        "report:read", "agent:read",
        "dashboard:read", "import-export:read", "import-export:write"
    ],
    "viewer": [
        # 只读用户
        "customer:read",
        "opportunity:read",
        "quote:read",
        "followup:read",
        "report:read",
        "dashboard:read"
    ]
}


class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    def has_permission(user_role: str, required_permission: str) -> bool:
        """
        检查用户角色是否有所需权限
        
        Args:
            user_role: 用户角色代码
            required_permission: 所需权限（格式: resource:action）
        
        Returns:
            是否有权限
        """
        # 获取角色权限
        role_permissions = DEFAULT_PERMISSIONS.get(user_role, [])
        
        # 超级管理员拥有所有权限
        if "*" in role_permissions:
            return True
        
        # 检查精确匹配
        if required_permission in role_permissions:
            return True
        
        # 检查通配符匹配（例如：customer:* 匹配 customer:read）
        resource = required_permission.split(":")[0]
        if f"{resource}:*" in role_permissions:
            return True
        
        return False
    
    @staticmethod
    def check_permission(user: User, required_permission: str) -> bool:
        """
        检查用户是否有权限
        
        Args:
            user: 用户对象
            required_permission: 所需权限
        
        Returns:
            是否有权限
        """
        # 超级管理员跳过权限检查
        if user.is_superuser:
            return True
        
        # 获取用户角色
        if not user.role:
            return False
        
        return PermissionChecker.has_permission(user.role.code, required_permission)


def require_permission(permission: str):
    """
    权限检查装饰器
    
    用法:
        @router.post("/customers")
        @require_permission("customer:write")
        async def create_customer(...):
            ...
    
    Args:
        permission: 所需权限字符串
    
    Returns:
        装饰器函数
    """
    async def permission_dependency(
        current_user: User = Depends(get_current_user)
    ):
        if not PermissionChecker.check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要: {permission}"
            )
        return current_user
    
    return Depends(permission_dependency)


async def check_user_permission(
    user: User,
    required_permission: str,
    raise_exception: bool = True
) -> bool:
    """
    检查用户权限（函数形式）
    
    Args:
        user: 用户对象
        required_permission: 所需权限
        raise_exception: 是否抛出异常
    
    Returns:
        是否有权限
    
    Raises:
        HTTPException: 权限不足且raise_exception=True时
    """
    has_perm = PermissionChecker.check_permission(user, required_permission)
    
    if not has_perm and raise_exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足，需要: {required_permission}"
        )
    
    return has_perm


def filter_by_organization(query, model, user: User):
    """
    数据隔离过滤器
    
    根据用户角色自动过滤数据：
    - 超级管理员：可见所有数据
    - 管理员：可见组织内所有数据
    - 经理：可见团队内所有数据
    - 销售/普通用户：仅可见自己创建的数据
    
    Args:
        query: SQLAlchemy查询对象
        model: 数据模型类
        user: 当前用户
    
    Returns:
        过滤后的查询对象
    """
    # 超级管理员可见所有数据
    if user.is_superuser:
        return query
    
    # 确保模型有organization_id字段
    if not hasattr(model, 'organization_id'):
        return query
    
    # 过滤组织数据
    query = query.where(model.organization_id == user.organization_id)
    
    # 如果是管理员，可见组织内所有数据
    if user.role and user.role.code in ["admin", "super_admin"]:
        return query
    
    # 如果是经理，可见团队内所有数据
    if user.role and user.role.code == "manager":
        if hasattr(model, 'created_by') and user.team_id:
            # 需要JOIN users表来过滤团队成员数据
            from app.models.models import User as UserModel
            query = query.join(UserModel, UserModel.id == model.created_by)
            query = query.where(UserModel.team_id == user.team_id)
        return query
    
    # 普通用户仅可见自己创建的数据
    if hasattr(model, 'created_by'):
        query = query.where(model.created_by == user.id)
    
    return query


async def check_data_access(
    db: AsyncSession,
    user: User,
    model_class,
    entity_id: int,
    permission: str = "read"
) -> Optional[object]:
    """
    检查数据访问权限并返回实体
    
    Args:
        db: 数据库会话
        user: 当前用户
        model_class: 模型类
        entity_id: 实体ID
        permission: 权限类型（read/write/delete）
    
    Returns:
        实体对象，无权限返回None
    
    Raises:
        HTTPException: 无权限时抛出403或404错误
    """
    # 查询实体
    result = await db.execute(
        select(model_class).where(model_class.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    
    # 实体不存在
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    
    # 超级管理员有所有权限
    if user.is_superuser:
        return entity
    
    # 检查组织权限
    if hasattr(entity, 'organization_id'):
        if entity.organization_id != user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此资源"
            )
    
    # 检查数据所有者
    if hasattr(entity, 'created_by'):
        # 管理员可以访问组织内所有数据
        if user.role and user.role.code in ["admin", "super_admin"]:
            return entity
        
        # 经理可以访问团队内数据
        if user.role and user.role.code == "manager":
            # 需要查询创建者的团队
            from app.models.models import User as UserModel
            creator_result = await db.execute(
                select(UserModel).where(UserModel.id == entity.created_by)
            )
            creator = creator_result.scalar_one_or_none()
            if creator and creator.team_id == user.team_id:
                return entity
        
        # 普通用户只能访问自己的数据
        if entity.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此资源"
            )
    
    return entity


def get_permission_list() -> dict:
    """
    获取所有可用权限列表
    
    Returns:
        权限字典
    """
    return DEFAULT_PERMISSIONS
