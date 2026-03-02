"""
认证模块单元测试
"""
import pytest
from datetime import datetime, timedelta

from app.core.auth import (
    verify_password, hash_password, create_access_token,
    decode_access_token, create_password_reset_token,
    verify_password_reset_token
)


class TestPasswordHashing:
    """密码哈希测试"""
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_hash_password(self):
        """测试密码哈希"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_hash_password_different_each_time(self):
        """测试相同密码生成不同哈希"""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # bcrypt每次生成不同的哈希
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_password_correct(self):
        """测试密码验证 - 正确密码"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_password_incorrect(self):
        """测试密码验证 - 错误密码"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password("wrongpassword", hashed) is False
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_password_empty(self):
        """测试密码验证 - 空密码"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password("", hashed) is False


class TestJWTToken:
    """JWT Token测试"""
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_create_access_token(self):
        """测试创建访问令牌"""
        # JWT规范要求sub必须是字符串
        data = {"sub": "1", "role": "admin"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_decode_access_token_valid(self):
        """测试解码有效令牌"""
        # JWT规范要求sub必须是字符串
        data = {"sub": "1", "role": "admin"}
        token = create_access_token(data)
        
        decoded = decode_access_token(token)
        
        assert decoded is not None
        assert decoded["sub"] == "1"
        assert decoded["role"] == "admin"
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_decode_access_token_invalid(self):
        """测试解码无效令牌"""
        invalid_token = "invalid.token.here"
        
        decoded = decode_access_token(invalid_token)
        
        assert decoded is None
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_create_access_token_with_expiry(self):
        """测试创建带过期时间的令牌"""
        # JWT规范要求sub必须是字符串
        data = {"sub": "1"}
        expires = timedelta(hours=1)
        token = create_access_token(data, expires)
        
        decoded = decode_access_token(token)
        
        assert decoded is not None
        assert "exp" in decoded
        # 验证过期时间在合理范围内
        exp_time = datetime.utcfromtimestamp(decoded["exp"])
        now = datetime.utcnow()
        # 允许一定的时间误差
        assert exp_time > now - timedelta(minutes=5)
        assert exp_time < now + timedelta(hours=2)


class TestPasswordReset:
    """密码重置测试"""
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_create_password_reset_token(self):
        """测试创建密码重置令牌"""
        email = "test@example.com"
        token = create_password_reset_token(email)
        
        assert token is not None
        assert isinstance(token, str)
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_password_reset_token_valid(self):
        """测试验证有效的密码重置令牌"""
        email = "test@example.com"
        token = create_password_reset_token(email)
        
        result = verify_password_reset_token(token)
        
        assert result == email
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_password_reset_token_invalid(self):
        """测试验证无效的密码重置令牌"""
        invalid_token = "invalid.token.here"
        
        result = verify_password_reset_token(invalid_token)
        
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_password_reset_token_wrong_type(self):
        """测试验证错误类型的令牌"""
        # 创建普通访问令牌，不是重置令牌
        # JWT规范要求sub必须是字符串
        data = {"sub": "test@example.com"}
        normal_token = create_access_token(data)
        
        result = verify_password_reset_token(normal_token)
        
        assert result is None  # 应该返回None因为type不是"reset"
