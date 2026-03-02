---
name: salesGPT 全面测试与前后端联调
overview: 对 salesGPT 项目进行全面的后端单元测试、集成测试、API测试，以及前后端联调验证
todos:
  - id: check-environment
    content: 检查 Python 和 Node.js 环境是否已安装
    status: completed
  - id: backend-install
    content: 安装后端 Python 依赖
    status: completed
    dependencies:
      - check-environment
  - id: backend-migrate
    content: 运行数据库迁移初始化表结构
    status: completed
    dependencies:
      - backend-install
  - id: backend-start
    content: 启动后端 FastAPI 服务
    status: completed
    dependencies:
      - backend-migrate
  - id: frontend-install
    content: 安装前端 npm 依赖
    status: completed
    dependencies:
      - check-environment
  - id: frontend-start
    content: 启动前端 Vite 开发服务器
    status: completed
    dependencies:
      - frontend-install
      - backend-start
  - id: verify-services
    content: 验证前后端服务正常运行
    status: completed
    dependencies:
      - frontend-start
---

## 用户需求

启动 salesGPT 项目，包含前后端服务的完整启动流程。

## 项目状态

- 后端：已有 .env 配置，使用 SQLite 数据库
- 前端：端口 3000，API 代理到后端 8000
- 数据库迁移：alembic/versions/ 已有迁移文件

## 技术环境

- 后端：Python 3.11+ / FastAPI / SQLAlchemy / SQLite
- 前端：Node.js 18+ / Vue 3 / Vite / Element Plus
- 端口：后端 8000，前端 3000

## 启动流程

### 后端启动步骤

1. 进入 backend 目录
2. 激活 Python 虚拟环境（如已创建）
3. 安装依赖：`pip install -r requirements.txt`
4. 运行数据库迁移：`alembic upgrade head`
5. 启动服务：`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### 前端启动步骤

1. 进入 frontend 目录
2. 安装依赖：`npm install`
3. 启动开发服务器：`npm run dev`

### 验证服务

- 后端健康检查：http://localhost:8000/health
- 后端 API 文档：http://localhost:8000/docs
- 前端页面：http://localhost:3000