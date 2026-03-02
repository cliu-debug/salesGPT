# AI销售助手 部署文档

## 目录

1. [系统要求](#系统要求)
2. [环境准备](#环境准备)
3. [本地开发部署](#本地开发部署)
4. [生产环境部署](#生产环境部署)
5. [Docker部署](#docker部署)
6. [数据库配置](#数据库配置)
7. [Nginx配置](#nginx配置)
8. [监控和日志](#监控和日志)
9. [故障排除](#故障排除)

---

## 系统要求

### 最低配置

- **CPU**: 2核
- **内存**: 4GB
- **存储**: 20GB SSD
- **操作系统**: Ubuntu 20.04+ / CentOS 7+ / Windows Server 2019+

### 推荐配置

- **CPU**: 4核+
- **内存**: 8GB+
- **存储**: 50GB+ SSD
- **操作系统**: Ubuntu 22.04 LTS

### 软件要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ / SQLite 3
- Redis 6+ (可选，用于缓存)
- Nginx (生产环境)

---

## 环境准备

### 1. 安装Python

```bash
# Ubuntu
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# CentOS
sudo yum install python3.10 python3.10-pip
```

### 2. 安装Node.js

```bash
# 使用nvm安装
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
```

### 3. 安装PostgreSQL

```bash
# Ubuntu
sudo apt install postgresql postgresql-contrib

# CentOS
sudo yum install postgresql-server postgresql-contrib

# 初始化并启动
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 4. 安装Redis (可选)

```bash
# Ubuntu
sudo apt install redis-server

# 启动
sudo systemctl start redis
sudo systemctl enable redis
```

---

## 本地开发部署

### 后端部署

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Linux/Mac
source venv/bin/activate
# Windows
.\venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
# 编辑.env文件，设置必要的配置

# 6. 初始化数据库
alembic upgrade head

# 7. 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端部署

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 配置API地址
# 编辑 .env.development
VITE_API_BASE_URL=http://localhost:8000

# 4. 启动开发服务器
npm run dev
```

---

## 生产环境部署

### 1. 后端部署

```bash
# 创建部署用户
sudo useradd -m -s /bin/bash salesapp
sudo su - salesapp

# 克隆代码
git clone https://your-repo/opc.git
cd opc/backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env
```

**生产环境.env配置**:

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/sales_db

# 安全配置
SECRET_KEY=your-very-secure-secret-key-at-least-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# AI服务
DASHSCOPE_API_KEY=your-dashscope-api-key
DASHSCOPE_MODEL=qwen-max

# Redis (可选)
REDIS_URL=redis://localhost:6379/0

# 应用配置
APP_NAME=AI销售助手
APP_VERSION=1.0.0
DEBUG=false

# 数据库连接池
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_PRE_PING=true
```

### 2. 创建Systemd服务

```bash
sudo nano /etc/systemd/system/sales-app.service
```

```ini
[Unit]
Description=salesGPT API
After=network.target postgresql.service

[Service]
Type=notify
User=salesapp
Group=salesapp
WorkingDirectory=/home/salesapp/opc/backend
Environment="PATH=/home/salesapp/opc/backend/venv/bin"
ExecStart=/home/salesapp/opc/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 启动服务
sudo systemctl daemon-reload
sudo systemctl start sales-app
sudo systemctl enable sales-app

# 检查状态
sudo systemctl status sales-app
```

### 3. 前端构建部署

```bash
cd frontend

# 安装依赖
npm install

# 配置生产环境API
nano .env.production
```

```bash
VITE_API_BASE_URL=https://api.yourdomain.com
```

```bash
# 构建
npm run build

# 部署到Nginx目录
sudo cp -r dist/* /var/www/sales-app/
```

---

## Docker部署

### 1. 创建Dockerfile (后端)

```dockerfile
# backend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. 创建Dockerfile (前端)

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# 使用Nginx服务
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 3. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: sales_db
      POSTGRES_USER: sales_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7-alpine
    restart: always

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://sales_user:secure_password@db:5432/sales_db
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      DASHSCOPE_API_KEY: ${DASHSCOPE_API_KEY}
    depends_on:
      - db
      - redis
    ports:
      - "8000:8000"
    restart: always

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: always

volumes:
  postgres_data:
```

```bash
# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

---

## 数据库配置

### PostgreSQL配置

```sql
-- 创建数据库和用户
CREATE DATABASE sales_db;
CREATE USER sales_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE sales_db TO sales_user;

-- 连接到数据库
\c sales_db

-- 授予schema权限
GRANT ALL ON SCHEMA public TO sales_user;
```

### 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 数据库备份

```bash
# 备份
pg_dump -U sales_user -d sales_db > backup_$(date +%Y%m%d).sql

# 恢复
psql -U sales_user -d sales_db < backup_20240115.sql
```

---

## Nginx配置

```nginx
# /etc/nginx/sites-available/sales-app
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL证书
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # 前端
    location / {
        root /var/www/sales-app;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket支持
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;
}
```

---

## 监控和日志

### 应用日志

日志文件位置: `backend/logs/`

```bash
# 查看实时日志
tail -f backend/logs/app.log

# 日志轮转配置
sudo nano /etc/logrotate.d/sales-app
```

```
/home/salesapp/opc/backend/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 salesapp salesapp
}
```

### 性能监控

```bash
# 访问监控端点
curl http://localhost:8000/api/monitoring/health
curl http://localhost:8000/api/monitoring/metrics
```

### Prometheus监控 (可选)

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'sales-app'
    static_configs:
      - targets: ['localhost:8000']
```

---

## 故障排除

### 常见问题

**1. 数据库连接失败**

```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 检查连接
psql -U sales_user -d sales_db -h localhost
```

**2. 后端服务无法启动**

```bash
# 检查日志
journalctl -u sales-app -f

# 检查端口占用
sudo lsof -i :8000
```

**3. 前端无法访问API**

- 检查CORS配置
- 检查Nginx代理配置
- 检查防火墙规则

**4. AI服务调用失败**

- 检查DASHSCOPE_API_KEY是否正确
- 检查网络连接
- 检查API配额

### 性能优化

1. **数据库优化**
   - 添加索引
   - 配置连接池
   - 定期VACUUM

2. **应用优化**
   - 启用Redis缓存
   - 调整worker数量
   - 启用Gzip压缩

3. **系统优化**
   ```bash
   # 增加文件描述符限制
   echo "* soft nofile 65536" >> /etc/security/limits.conf
   echo "* hard nofile 65536" >> /etc/security/limits.conf
   ```

---

## 安全建议

1. 定期更新系统和依赖
2. 使用HTTPS
3. 配置防火墙
4. 启用日志审计
5. 定期备份数据库
6. 使用强密码
7. 限制API访问频率
