<div align="center">

# 🚀 salesGPT

**企业级智能销售管理系统**

*让一个人也能像团队一样高效卖货*

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.4+-42b883.svg" alt="Vue">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/Tests-154%20passed-brightgreen.svg" alt="Tests">
</p>

[在线演示](#) · [快速开始](#-快速开始) · [功能特性](#-特性) · [技术架构](#-技术架构)

</div>

---

## 🎯 为什么选择 salesGPT？

| 特性 | salesGPT | 传统 CRM |
|------|----------|----------|
| AI 智能分析 | ✅ 通义千问深度集成 | ❌ 无或付费插件 |
| 部署复杂度 | ✅ 一键 Docker 部署 | ❌ 需要专业运维 |
| 代码质量 | ✅ 154 个测试全覆盖 | ❌ 黑盒无法验证 |
| 定制开发 | ✅ 开源可自行修改 | ❌ SaaS 无法定制 |
| 使用成本 | ✅ 完全免费开源 | ❌ 按人头收费 |

## 📸 功能展示

> 📷 请添加项目截图到 `docs/images/` 目录

| 仪表盘 | 客户管理 | AI 分析 |
|:------:|:--------:|:-------:|
| Dashboard | Clients | AI Analysis |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │Dashboard│  │ Customer│  │Opportunity│  │  Quote  │            │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
└───────┼────────────┼────────────┼────────────┼──────────────────┘
        │            │            │            │
        └────────────┴─────┬──────┴────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────┼─────────────────────────────────────┐
│                   Backend (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    API Gateway Layer                      │ │
│  │  Auth │ Customer │ Opportunity │ Quote │ Import/Export   │ │
│  └────────────────────────┬─────────────────────────────────┘ │
│                           │                                    │
│  ┌────────────────────────┼─────────────────────────────────┐ │
│  │                   Service Layer                           │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │ │
│  │  │ AI Svc   │ │ Monitor  │ │ Analytics│ │  Alert Svc  │  │ │
│  │  │(Qwen)    │ │ Agent    │ │ Service  │ │             │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────────┘  │ │
│  └────────────────────────┬─────────────────────────────────┘ │
│                           │                                    │
│  ┌────────────────────────┼─────────────────────────────────┐ │
│  │                   Data Layer                              │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐           │ │
│  │  │PostgreSQL│    │  Redis   │    │  SQLite  │           │ │
│  │  │ (prod)   │    │ (cache)  │    │  (dev)   │           │ │
│  │  └──────────┘    └──────────┘    └──────────┘           │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## ✨ 特性

- 🤖 **AI 智能分析** - 客户分析、成交概率预测、智能话术推荐
- 👥 **完整客户管理** - 客户信息管理、销售机会跟踪、跟进记录
- 📊 **数据仪表盘** - 销售漏斗、业绩统计、趋势分析
- 🔐 **权限管理系统** - RBAC 角色权限、数据隔离
- 📦 **批量导入导出** - Excel 批量导入导出
- 🔄 **自动化任务** - AI Agent 自动监控和预警
- 🚀 **高性能** - Redis 缓存、数据库索引优化

## 🌟 项目亮点

### 1. AI 赋能销售
- **智能客户分析** - AI 自动分析客户画像，生成跟进策略
- **成交概率预测** - 基于历史数据预测成交可能性
- **智能话术推荐** - 根据场景自动生成最佳话术
- **自动任务提醒** - AI Agent 监控销售机会，及时提醒跟进

### 2. 企业级架构
- **完整权限体系** - 5种角色（超管/总监/经理/销售/查看），支持团队数据隔离
- **多租户支持** - 团队级数据隔离，保障数据安全
- **审计日志** - 完整操作记录，可追溯可审计

### 3. 高性能设计
- **二级缓存架构** - L1 本地缓存 + L2 Redis 缓存，响应速度提升 10 倍
- **数据库优化** - 30+ 组合索引，复杂查询毫秒级响应
- **连接池管理** - PostgreSQL 连接池，高并发支持

### 4. 完善的容错机制
- **AI 服务降级** - 通义千问 API 不可用时自动降级到基础模式
- **重试机制** - 指数退避重试，确保请求成功率
- **Token 监控** - 智能控制 AI 调用成本

### 5. 开发者友好
- **完整测试覆盖** - 单元测试 + 集成测试，代码质量有保障
- **CI/CD 自动化** - GitHub Actions 自动测试、构建、部署
- **详细文档** - API 文档、部署指南、用户手册齐全
- **Docker 支持** - 一键部署，生产环境轻松上线

### 6. 可扩展性强
- **模块化设计** - 13 个独立服务模块，易于扩展
- **Webhook 支持** - 可对接 CRM、企业微信、钉钉等外部系统
- **AI 服务可替换** - 预留 AI 接口，可接入其他大模型

## 👥 适合人群

- **个人销售/自由职业者** - 一人团队也能高效管理客户
- **中小企业销售团队** - 完整的客户管理和权限系统
- **学习者** - 企业级全栈项目参考
- **二次开发者** - 模块化设计易于扩展

## 🏗️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 |
| 数据库 | PostgreSQL / SQLite |
| 缓存 | Redis |
| 认证 | JWT + bcrypt |
| 前端 | Vue 3 + Element Plus + Pinia |
| AI 服务 | 通义千问 (DashScope) |
| 部署 | Docker + GitHub Actions |

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (可选，测试可用 SQLite)

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/salesgpt.git
cd salesgpt
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库和 API 密钥
```

#### 环境变量说明

| 变量名 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `DATABASE_URL` | ✅ | 数据库连接地址 | `postgresql+asyncpg://user:pass@localhost:5432/salesgpt` |
| `SECRET_KEY` | ✅ | JWT 密钥，生产环境必须修改 | `openssl rand -hex 32` 生成 |
| `ALLOWED_ORIGINS` | ✅ | 允许的跨域前端地址 | `http://localhost:5173` |
| `DASHSCOPE_API_KEY` | - | 通义千问 API 密钥 | 申请地址：https://dashscope.console.aliyun.com |
| `DASHSCOPE_MODEL` | - | AI 模型 | `qwen-max` |
| `REDIS_URL` | - | Redis 地址（可选，用于缓存） | `redis://localhost:6379/0` |
| `DEBUG` | - | 调试模式 | `true` / `false` |

### 3. 启动后端

```bash
# 运行数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload
```

后端服务将在 http://localhost:8000 运行

### 4. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env

# 启动开发服务器
npm run dev
```

前端应用将在 http://localhost:5173 运行

## 📖 文档

- [API 文档](docs/API.md)
- [部署指南](docs/DEPLOYMENT.md)
- [用户手册](docs/USER_MANUAL.md)

## 🧪 测试

```bash
cd backend

# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html
```

## 🐳 Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

## 📁 项目结构

```
salesgpt/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 端点
│   │   ├── core/           # 核心模块
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── services/       # 业务服务
│   │   └── middleware/     # 中间件
│   ├── tests/              # 测试套件
│   └── alembic/            # 数据库迁移
│
├── frontend/               # Vue3 前端
│   └── src/
│       ├── views/          # 页面组件
│       ├── stores/         # Pinia 状态管理
│       └── components/     # UI 组件
│
├── docs/                   # 文档
├── scripts/               # 运维脚本
└── .github/               # GitHub Actions
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！请先阅读 [贡献指南](CONTRIBUTING.md)。

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 了解更多。

## 🗺️ Roadmap

### v1.1 (计划中)
- [ ] 移动端适配
- [ ] 企业微信/钉钉通知集成
- [ ] 数据导入模板优化
- [ ] 自定义报表功能

### v1.2 (规划中)
- [ ] 多语言支持 (i18n)
- [ ] SaaS 多租户模式
- [ ] 高级数据可视化
- [ ] AI 话术训练自定义

### 欢迎贡献
有好的想法？欢迎提交 [Issue](https://github.com/your-repo/salesgpt/issues) 或 [PR](https://github.com/your-repo/salesgpt/pulls)！

## 📞 交流

<p>
  <a href="https://github.com/your-repo/salesgpt/issues">问题反馈</a> · 
  <a href="https://github.com/your-repo/salesgpt/discussions">功能讨论</a>
</p>

## 📝 更新日志

查看完整更新日志：[CHANGELOG](CHANGELOG.md)

### v1.0.0 (Latest)

- ✨ AI 智能客户分析
- ✨ 完整客户管理 CRM
- ✨ RBAC 权限系统
- ✨ 数据仪表盘
- ✨ 自动化监控告警
- ✨ 批量导入导出

---

## ❤️ 贡献者

[![Contributors](https://contrib.rocks/image?repo=your-repo/salesgpt)](https://github.com/your-repo/salesgpt/graphs/contributors)

---

## 🏆 致谢

<p>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.109+-green?style=flat-square" alt="FastAPI"></a>
  <a href="https://vuejs.org/"><img src="https://img.shields.io/badge/Vue.js-3.4+-42b883?style=flat-square" alt="Vue.js"></a>
  <a href="https://element-plus.org/"><img src="https://img.shields.io/badge/Element%20Plus-2.x-409eff?style=flat-square" alt="Element Plus"></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-14+-336791?style=flat-square" alt="PostgreSQL"></a>
  <a href="https://dashscope.console.aliyun.com/"><img src="https://img.shields.io/badge/通义千问-AI-ff6a00?style=flat-square" alt="通义千问"></a>
</p>

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star 支持一下！**

*这将激励我们持续改进和添加更多功能*

</div>
