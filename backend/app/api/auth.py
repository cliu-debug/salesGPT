"""
认证API端点 - 用户登录、注册、权限管理
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    get_current_superuser
)
from app.core.config import settings
from app.core.permissions import DEFAULT_PERMISSIONS
from app.models.models import User, Role, Team, Organization, AuditLog
from app.schemas.schemas import (
    UserLogin,
    UserRegister,
    Token,
    UserResponse,
    UserUpdate,
    PasswordChange,
    RoleCreate,
    RoleResponse,
    TeamCreate,
    TeamResponse,
    OrganizationResponse
)

router = APIRouter()


@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    """
    # 查询用户（预加载关系）
    result = await db.execute(
        select(User)
        .options(selectinload(User.role), selectinload(User.team), selectinload(User.organization))
        .where(User.username == user_data.username)
    )
    user = result.scalar_one_or_none()
    
    # 验证用户存在
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用"
        )
    
    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    
    # 记录审计日志
    try:
        audit_log = AuditLog(
            user_id=user.id,
            username=user.username,
            organization_id=user.organization_id,
            action="login",
            entity_type="user",
            entity_id=user.id,
            entity_name=user.username,
            new_values={"login_time": datetime.utcnow().isoformat()}
        )
        db.add(audit_log)
    except Exception:
        pass  # 审计日志失败不影响登录
    
    await db.commit()
    
    # 构建响应 - 使用已加载的关系或安全访问
    role_name = user.role.name if user.role else None
    team_name = user.team.name if user.team else None
    organization_name = user.organization.name if user.organization else None
    
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        avatar=user.avatar,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        role_id=user.role_id,
        role_name=role_name,
        team_id=user.team_id,
        team_name=team_name,
        organization_id=user.organization_id,
        organization_name=organization_name,
        created_at=user.created_at,
        last_login=user.last_login
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )


@router.post("/register", response_model=Token, summary="用户注册")
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册（首次注册会自动创建组织）
    
    - **username**: 用户名（3-50字符）
    - **email**: 邮箱地址
    - **password**: 密码（至少6字符）
    - **full_name**: 全名（可选）
    """
    # 检查用户名是否已存在
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 检查邮箱是否已存在
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建组织（首次注册）
    organization = Organization(
        name=f"{user_data.username}的组织",
        slug=f"{user_data.username}-org-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    db.add(organization)
    await db.flush()
    
    # 创建默认角色 - 使用组织ID作为前缀确保唯一性
    org_prefix = f"org{organization.id}_"
    roles_data = [
        {"name": "管理员", "code": f"{org_prefix}admin", "base_code": "admin", "permissions": DEFAULT_PERMISSIONS["admin"]},
        {"name": "经理", "code": f"{org_prefix}manager", "base_code": "manager", "permissions": DEFAULT_PERMISSIONS["manager"]},
        {"name": "销售", "code": f"{org_prefix}sales", "base_code": "sales", "permissions": DEFAULT_PERMISSIONS["sales"]},
        {"name": "只读用户", "code": f"{org_prefix}viewer", "base_code": "viewer", "permissions": DEFAULT_PERMISSIONS["viewer"]}
    ]
    
    admin_role = None
    for role_data in roles_data:
        role = Role(
            name=role_data["name"],
            code=role_data["code"],
            permissions=role_data["permissions"],
            organization_id=organization.id,
            is_system=True
        )
        db.add(role)
        if role_data["base_code"] == "admin":
            await db.flush()
            admin_role = role
    
    await db.flush()
    
    # 创建默认团队
    team = Team(
        name="默认团队",
        description="默认团队",
        organization_id=organization.id
    )
    db.add(team)
    await db.flush()
    
    # 如果没有获取到管理员角色，重新查询
    if not admin_role:
        result = await db.execute(
            select(Role).where(
                Role.code == f"{org_prefix}admin",
                Role.organization_id == organization.id
            )
        )
        admin_role = result.scalar_one()
    
    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        role_id=admin_role.id,
        team_id=team.id,
        organization_id=organization.id,
        is_active=True,
        is_superuser=True  # 第一个用户为超级管理员
    )
    db.add(user)
    await db.commit()
    
    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # 构建响应
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        avatar=user.avatar,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        role_id=user.role_id,
        role_name=admin_role.name,
        team_id=user.team_id,
        team_name=team.name,
        organization_id=user.organization_id,
        organization_name=organization.name,
        created_at=user.created_at,
        last_login=None
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前登录用户的详细信息"""
    # 刷新用户对象以加载关系
    await db.refresh(current_user, ["role", "team", "organization"])
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar=current_user.avatar,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        role_id=current_user.role_id,
        role_name=current_user.role.name if current_user.role else None,
        team_id=current_user.team_id,
        team_name=current_user.team.name if current_user.team else None,
        organization_id=current_user.organization_id,
        organization_name=current_user.organization.name if current_user.organization else None,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.put("/me", response_model=UserResponse, summary="更新当前用户信息")
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户信息"""
    # 更新字段
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.avatar is not None:
        current_user.avatar = user_data.avatar
    if user_data.email is not None:
        # 检查邮箱是否已被使用
        result = await db.execute(
            select(User).where(
                User.email == user_data.email,
                User.id != current_user.id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
        current_user.email = user_data.email
    if user_data.preferences is not None:
        current_user.preferences = user_data.preferences
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar=current_user.avatar,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        role_id=current_user.role_id,
        role_name=current_user.role.name if current_user.role else None,
        team_id=current_user.team_id,
        team_name=current_user.team.name if current_user.team else None,
        organization_id=current_user.organization_id,
        organization_name=current_user.organization.name if current_user.organization else None,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.post("/change-password", summary="修改密码")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改当前用户密码"""
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码不正确"
        )
    
    # 更新密码
    current_user.password_hash = hash_password(password_data.new_password)
    await db.commit()
    
    return {"message": "密码修改成功"}


@router.get("/permissions", summary="获取权限列表")
async def get_permissions(
    current_user: User = Depends(get_current_user)
):
    """获取所有可用权限列表"""
    return {
        "permissions": DEFAULT_PERMISSIONS,
        "user_role": current_user.role.code if current_user.role else None
    }


@router.post("/logout", summary="用户登出")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """用户登出（记录审计日志）"""
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        organization_id=current_user.organization_id,
        action="logout",
        entity_type="user",
        entity_id=current_user.id,
        entity_name=current_user.username
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "登出成功"}
  
