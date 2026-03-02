---
name: 全面E2E测试计划
overview: 为企业级智能销售管理系统（FastAPI + Vue 3）制定端到端（E2E）全面测试方案，覆盖所有API模块、权限系统、数据隔离和前后端集成。
todos:
  - id: env-setup
    content: 检查并安装测试依赖，配置测试环境变量
    status: completed
  - id: run-existing-tests
    content: 运行现有单元测试和API测试，生成覆盖率报告
    status: completed
    dependencies:
      - env-setup
  - id: test-quotes
    content: 创建报价单API测试模块 test_api_quotes.py
    status: completed
    dependencies:
      - run-existing-tests
  - id: test-followups
    content: 创建跟进记录API测试模块 test_api_followups.py
    status: completed
    dependencies:
      - run-existing-tests
  - id: test-dashboard
    content: 创建仪表盘API测试模块 test_api_dashboard.py
    status: completed
    dependencies:
      - run-existing-tests
  - id: test-agent
    content: 创建AI代理API测试模块 test_api_agent.py（验证修复接口）
    status: completed
    dependencies:
      - run-existing-tests
  - id: test-analytics
    content: 创建数据分析API测试模块 test_api_analytics.py
    status: completed
    dependencies:
      - run-existing-tests
  - id: test-import-export
    content: 创建导入导出API测试模块 test_api_import_export.py
    status: completed
    dependencies:
      - run-existing-tests
  - id: test-monitoring
    content: 创建监控API测试模块 test_api_monitoring.py
    status: completed
    dependencies:
      - run-existing-tests
  - id: run-full-tests
    content: 执行全量测试并生成覆盖率报告
    status: completed
    dependencies:
      - test-quotes
      - test-followups
      - test-dashboard
      - test-agent
      - test-analytics
      - test-import-export
      - test-monitoring
---

## 产品概述

对企业级智能销售管理系统进行全面测试，验证系统稳定性和功能完整性。

## 核心功能

- 运行现有单元测试和集成测试，验证核心功能
- 为缺失的API模块补充测试用例（报价单、跟进记录、仪表盘、AI代理、分析、导入导出、监控）
- 重点验证之前修复的API接口（/api/auth/me 和 /api/agent/alerts）
- 生成测试覆盖率报告
- 配置测试环境并执行全量测试

## 技术栈

- 后端测试框架：pytest + pytest-asyncio + pytest-cov
- 测试数据库：内存SQLite (aiosqlite)
- HTTP客户端：httpx AsyncClient
- 覆盖率工具：coverage + pytest-cov

## 测试架构

### 测试分层

```
测试金字塔:
├── E2E测试（前后端集成）
│   └── 关键业务流程测试
├── API集成测试
│   ├── 已有：auth, customers, opportunities
│   └── 待补充：quotes, followups, dashboard, agent, analytics, import_export, monitoring
└── 单元测试
    ├── 已有：auth, permissions, ai_service
    └── 待补充：monitoring_agent, data isolation
```

### 测试覆盖目标

- 代码覆盖率：≥80%
- API端点覆盖率：100%（11个API模块）
- 关键业务流程：100%

## 目录结构

```
backend/tests/
├── conftest.py                    # [已有] 测试配置和fixtures
├── test_unit_auth.py              # [已有] 认证单元测试
├── test_unit_permissions.py       # [已有] 权限单元测试
├── test_unit_ai_service.py        # [已有] AI服务单元测试
├── test_api_auth.py               # [已有] 认证API测试
├── test_api_customers.py          # [已有] 客户API测试
├── test_api_opportunities.py      # [已有] 机会API测试
├── test_api_quotes.py             # [NEW] 报价单API测试
├── test_api_followups.py          # [NEW] 跟进记录API测试
├── test_api_dashboard.py          # [NEW] 仪表盘API测试
├── test_api_agent.py              # [NEW] AI代理API测试（含修复接口验证）
├── test_api_analytics.py          # [NEW] 数据分析API测试
├── test_api_import_export.py      # [NEW] 导入导出API测试
└── test_api_monitoring.py         # [NEW] 监控API测试
```

## 实现方案

### 1. 环境准备与验证

- 检查后端依赖安装（pytest, pytest-asyncio, pytest-cov等）
- 验证测试数据库配置（内存SQLite）
- 运行现有测试确认环境正常

### 2. 现有测试执行

- 运行全部单元测试
- 运行全部API集成测试
- 生成当前覆盖率报告

### 3. 新增API测试模块

每个测试模块遵循现有模式：

- 测试CRUD操作（创建、读取、更新、删除）
- 测试权限控制（不同角色的访问权限）
- 测试数据隔离（组织级别隔离）
- 测试边界条件（无效输入、不存在的资源等）

### 4. 修复接口专项测试

- `/api/auth/me`：验证用户关系预加载
- `/api/agent/alerts`：验证方法签名和数据隔离

### 5. 测试报告

- 生成HTML覆盖率报告
- 统计各模块测试通过率
- 标识未覆盖的代码路径

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 探索项目代码结构，查找API端点定义和依赖关系
- Expected outcome: 获取所有API端点的完整信息，确保测试用例覆盖所有功能