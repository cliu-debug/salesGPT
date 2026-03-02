# AI销售助手 API 文档

## 概述

AI销售助手提供RESTful API接口，支持客户管理、销售机会、报价单、跟进记录等核心业务功能，以及AI智能助手服务。

**基础URL**: `http://your-domain:8000`

**API版本**: v1.0.0

**认证方式**: Bearer Token (JWT)

## 快速开始

### 获取Token

```bash
# 登录获取Token
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

### 使用Token访问API

```bash
# 在请求头中携带Token
curl -X GET "http://localhost:8000/api/customers/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 认证接口 `/api/auth`

### 用户登录

```
POST /api/auth/login
```

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "管理员",
    "role_name": "admin",
    "organization_name": "示例公司"
  }
}
```

### 用户注册

```
POST /api/auth/register
```

**请求体**:
```json
{
  "username": "string (3-50字符)",
  "email": "string (有效邮箱)",
  "password": "string (至少6字符)",
  "full_name": "string (可选)"
}
```

### 获取当前用户信息

```
GET /api/auth/me
```

**请求头**: `Authorization: Bearer {token}`

### 修改密码

```
POST /api/auth/change-password
```

**请求体**:
```json
{
  "old_password": "string",
  "new_password": "string"
}
```

### 用户登出

```
POST /api/auth/logout
```

---

## 客户管理 `/api/customers`

### 获取客户列表

```
GET /api/customers/
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| skip | int | 跳过记录数（分页） |
| limit | int | 返回记录数 |
| search | string | 搜索关键词 |
| industry | string | 行业筛选 |
| source | string | 来源筛选 |

**响应**:
```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "name": "客户名称",
      "contact": "联系人",
      "phone": "13800138000",
      "email": "contact@example.com",
      "company": "公司名称",
      "industry": "互联网",
      "source": "线上推广",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### 创建客户

```
POST /api/customers/
```

**请求体**:
```json
{
  "name": "string (必填)",
  "contact": "string",
  "phone": "string",
  "email": "string",
  "company": "string",
  "industry": "string",
  "source": "string",
  "address": "string",
  "notes": "string"
}
```

### 获取单个客户

```
GET /api/customers/{customer_id}
```

### 更新客户

```
PUT /api/customers/{customer_id}
```

### 删除客户

```
DELETE /api/customers/{customer_id}
```

---

## 销售机会 `/api/opportunities`

### 获取机会列表

```
GET /api/opportunities/
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| stage | string | 阶段筛选 |
| customer_id | int | 客户ID筛选 |
| min_amount | float | 最小金额 |
| max_amount | float | 最大金额 |

### 创建销售机会

```
POST /api/opportunities/
```

**请求体**:
```json
{
  "customer_id": 1,
  "customer_name": "客户名称",
  "name": "项目名称",
  "amount": 50000.00,
  "stage": "initial",
  "probability": 30,
  "expected_date": "2024-03-30",
  "description": "项目描述"
}
```

**阶段说明**:
- `initial` - 初步接触 (概率: 20%)
- `requirement` - 需求确认 (概率: 40%)
- `proposal` - 方案报价 (概率: 60%)
- `negotiation` - 商务谈判 (概率: 80%)
- `won` - 成交 (概率: 100%)
- `lost` - 失败 (概率: 0%)

### 获取销售漏斗

```
GET /api/opportunities/stats/funnel
```

**响应**:
```json
{
  "stages": [
    {"stage": "initial", "count": 10, "amount": 500000},
    {"stage": "negotiation", "count": 5, "amount": 300000},
    {"stage": "won", "count": 2, "amount": 100000}
  ],
  "total_amount": 900000,
  "weighted_amount": 450000
}
```

---

## 报价管理 `/api/quotes`

### 创建报价单

```
POST /api/quotes/
```

**请求体**:
```json
{
  "customer_id": 1,
  "customer_name": "客户名称",
  "opportunity_id": 1,
  "items": [
    {
      "name": "产品名称",
      "description": "产品描述",
      "quantity": 1,
      "unit_price": 10000
    }
  ],
  "valid_until": "2024-03-30",
  "notes": "备注"
}
```

### 更新报价状态

```
PATCH /api/quotes/{quote_id}/status
```

**请求体**:
```json
{
  "status": "sent"
}
```

**状态说明**:
- `draft` - 草稿
- `sent` - 已发送
- `accepted` - 已接受
- `rejected` - 已拒绝
- `expired` - 已过期

---

## 跟进管理 `/api/follow-ups`

### 创建跟进记录

```
POST /api/follow-ups/
```

**请求体**:
```json
{
  "customer_id": 1,
  "customer_name": "客户名称",
  "content": "跟进内容",
  "next_action": "下一步计划",
  "next_date": "2024-02-20T10:00:00"
}
```

### 获取跟进记录

```
GET /api/follow-ups/
```

---

## 仪表盘 `/api/dashboard`

### 获取仪表盘数据

```
GET /api/dashboard/
```

**响应**:
```json
{
  "total_customers": 150,
  "total_opportunities": 45,
  "total_amount": 2500000,
  "conversion_rate": 35.5,
  "recent_activities": [...],
  "stage_distribution": {...},
  "monthly_trend": [...]
}
```

---

## AI助手 `/api/ai`

### AI对话

```
POST /api/ai/chat
```

**请求体**:
```json
{
  "message": "帮我分析这个客户的购买意向",
  "context": {
    "customer_id": 1
  }
}
```

### 客户分析

```
POST /api/ai/analyze/customer/{customer_id}
```

### 报价建议

```
POST /api/ai/suggest/quote
```

---

## 数据分析 `/api/analytics`

### 销售统计

```
GET /api/analytics/sales
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| start_date | date | 开始日期 |
| end_date | date | 结束日期 |
| group_by | string | 分组方式 (day/week/month) |

### 客户分析

```
GET /api/analytics/customers
```

---

## 导入导出 `/api/io`

### 导出数据

```
GET /api/io/export/{type}
```

**类型**: `customers`, `opportunities`, `quotes`

### 导入数据

```
POST /api/io/import/{type}
```

**请求体**: multipart/form-data (Excel文件)

---

## 监控 `/api/monitoring`

### 健康检查

```
GET /api/monitoring/health
```

### 性能指标

```
GET /api/monitoring/metrics
```

---

## 错误处理

### 错误响应格式

```json
{
  "detail": "错误描述",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 常见错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 422 | 验证错误 |
| 500 | 服务器内部错误 |

---

## 权限说明

### 角色权限矩阵

| 权限 | super_admin | admin | manager | sales | viewer |
|------|:-----------:|:-----:|:-------:|:-----:|:------:|
| 客户管理 | ✓ | ✓ | ✓ | ✓ | 只读 |
| 机会管理 | ✓ | ✓ | ✓ | ✓ | 只读 |
| 报价管理 | ✓ | ✓ | ✓ | ✓ | 只读 |
| 用户管理 | ✓ | ✓ | ✓ | ✗ | ✗ |
| 团队管理 | ✓ | ✓ | ✓ | ✗ | ✗ |
| 数据分析 | ✓ | ✓ | ✓ | ✓ | 只读 |
| 系统设置 | ✓ | ✓ | ✗ | ✗ | ✗ |

---

## 速率限制

- 普通接口: 100次/分钟
- AI接口: 20次/分钟

超过限制返回 `429 Too Many Requests`

---

## Swagger文档

访问 `http://your-domain:8000/docs` 查看交互式API文档

## OpenAPI规范

访问 `http://your-domain:8000/openapi.json` 获取OpenAPI规范文件
