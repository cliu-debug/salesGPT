"""
认证核心模块 - JWT认证、密码加密、Token管理
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌
    
    Args:
        data: 要编码的数据（通常包含用户ID）
        expires_delta: 过期时间增量
    
    Returns:
        JWT令牌字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码JWT令牌
    
    Args:
        token: JWT令牌字符串
    
    Returns:
        解码后的数据字典，失败返回None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前认证用户（依赖注入）
    
    Args:
        token: JWT令牌
        db: 数据库会话
    
    Returns:
        User对象
    
    Raises:
        HTTPException: 认证失败时抛出401错误
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 解码Token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    # 提取用户ID
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id: int = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception
    
    # 查询用户（预加载关系避免异步访问错误）
    try:
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.role),
                selectinload(User.team),
                selectinload(User.organization)
            )
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
    except Exception:
        raise credentials_exception
    
    # 验证用户存在且激活
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前激活用户
    
    Args:
        current_user: 当前用户
    
    Returns:
        激活的User对象
    
    Raises:
        HTTPException: 用户未激活时抛出403错误
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号未激活"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前超级管理员用户
    
    Args:
        current_user: 当前用户
    
    Returns:
        超级管理员User对象
    
    Raises:
        HTTPException: 不是超级管理员时抛出403错误
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
    return current_user


def create_password_reset_token(email: str) -> str:
    """
    创建密码重置令牌
    
    Args:
        email: 用户邮箱
    
    Returns:
        重置令牌
    """
    delta = timedelta(hours=24)  # 24小时有效期
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "type": "reset"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    验证密码重置令牌
    
    Args:
        token: 重置令牌
    
    Returns:
        邮箱地址，验证失败返回None
    """
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if decoded_token.get("type") != "reset":
            return None
        return decoded_token.get("sub")
    except JWTError:
        return None
 
