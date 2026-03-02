# 测试说明

## 测试结构

```
tests/
├── __init__.py
├── conftest.py              # 测试配置和fixtures
├── test_unit_auth.py        # 认证模块单元测试
├── test_unit_permissions.py # 权限模块单元测试
├── test_unit_ai_service.py  # AI服务单元测试
├── test_api_auth.py         # 认证API集成测试
├── test_api_customers.py    # 客户API集成测试
└── test_api_opportunities.py # 销售机会API集成测试
```

## 运行测试

### 安装测试依赖

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock fakeredis coverage
```

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定类型的测试

```bash
# 单元测试
pytest tests/ -v -m unit

# 集成测试
pytest tests/ -v -m integration

# API测试
pytest tests/ -v -m api

# 认证相关测试
pytest tests/ -v -m auth

# 权限相关测试
pytest tests/ -v -m permission
```

### 使用测试脚本

```bash
# 运行单元测试
python run_tests.py unit

# 运行集成测试
python run_tests.py integration

# 运行所有测试
python run_tests.py all

# 快速测试（跳过慢速测试）
python run_tests.py quick

# 生成覆盖率报告
python run_tests.py coverage
```

## 测试覆盖率

生成覆盖率报告：

```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
```

查看HTML报告：

```bash
# 在浏览器中打开 htmlcov/index.html
```

## 测试数据

测试使用内存SQLite数据库，每次测试后自动清理。

测试用户：
- `superadmin` - 超级管理员
- `admin` - 管理员
- `sales` - 销售人员
- `viewer` - 只读用户

默认密码：`password123`

## 编写新测试

### 单元测试示例

```python
@pytest.mark.unit
def test_function_name():
    """测试描述"""
    result = some_function()
    assert result == expected_value
```

### 集成测试示例

```python
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.asyncio
async def test_api_endpoint(client: AsyncClient, auth_headers):
    """测试API端点"""
    response = await client.get("/api/endpoint", headers=auth_headers)
    assert response.status_code == 200
```

### 使用fixtures

```python
# 使用预创建的测试数据
async def test_with_customer(test_customer):
    assert test_customer.name is not None

# 使用认证头
async def test_authenticated(client, auth_headers):
    response = await client.get("/api/protected", headers=auth_headers)
```
