#!/bin/bash

# ===========================================
# AI销售助手 - 自动部署脚本
# ===========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置变量
PROJECT_DIR="/home/salesapp/opc"
BACKUP_DIR="/home/salesapp/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 检查是否在正确的目录
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd $PROJECT_DIR

# ===========================================
# 部署前检查
# ===========================================
log_info "开始部署前检查..."

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    log_warn "检测到未提交的更改"
    read -p "是否继续部署？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
fi

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    # 检查PostgreSQL
    if systemctl is-active --quiet postgresql; then
        log_info "PostgreSQL 运行中"
    else
        log_error "PostgreSQL 未运行"
        exit 1
    fi
    
    # 检查Redis
    if systemctl is-active --quiet redis; then
        log_info "Redis 运行中"
    else
        log_warn "Redis 未运行，缓存功能将不可用"
    fi
}

# ===========================================
# 备份
# ===========================================
backup() {
    log_info "开始备份..."
    
    # 创建备份目录
    mkdir -p $BACKUP_DIR
    
    # 备份数据库
    log_info "备份数据库..."
    pg_dump -U sales_user sales_db > $BACKUP_DIR/db_$TIMESTAMP.sql
    
    # 备份环境配置
    log_info "备份配置文件..."
    cp backend/.env $BACKUP_DIR/env_$TIMESTAMP
    
    # 压缩备份
    tar -czf $BACKUP_DIR/backup_$TIMESTAMP.tar.gz \
        $BACKUP_DIR/db_$TIMESTAMP.sql \
        $BACKUP_DIR/env_$TIMESTAMP
    
    # 清理旧备份（保留最近7个）
    ls -t $BACKUP_DIR/backup_*.tar.gz | tail -n +8 | xargs -r rm
    
    log_info "备份完成: backup_$TIMESTAMP.tar.gz"
}

# ===========================================
# 拉取代码
# ===========================================
pull_code() {
    log_info "拉取最新代码..."
    
    # 获取当前分支
    BRANCH=$(git symbolic-ref --short HEAD)
    log_info "当前分支: $BRANCH"
    
    # 暂存本地更改
    git stash
    
    # 拉取代码
    git pull origin $BRANCH
    
    # 恢复暂存的更改
    git stash pop
    
    log_info "代码更新完成"
}

# ===========================================
# 后端部署
# ===========================================
deploy_backend() {
    log_info "开始部署后端..."
    
    cd $PROJECT_DIR/backend
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 安装/更新依赖
    log_info "更新依赖..."
    pip install -r requirements.txt
    
    # 运行数据库迁移
    log_info "运行数据库迁移..."
    alembic upgrade head
    
    # 收集静态文件（如有）
    # python manage.py collectstatic --noinput
    
    # 重启服务
    log_info "重启后端服务..."
    sudo systemctl restart sales-app
    
    # 等待服务启动
    sleep 5
    
    # 检查服务状态
    if systemctl is-active --quiet sales-app; then
        log_info "后端服务启动成功"
    else
        log_error "后端服务启动失败"
        journalctl -u sales-app -n 50
        exit 1
    fi
}

# ===========================================
# 前端部署
# ===========================================
deploy_frontend() {
    log_info "开始部署前端..."
    
    cd $PROJECT_DIR/frontend
    
    # 安装依赖
    log_info "安装前端依赖..."
    npm install
    
    # 构建生产版本
    log_info "构建前端..."
    npm run build
    
    # 部署到Nginx目录
    log_info "部署前端文件..."
    sudo cp -r dist/* /var/www/sales-app/
    
    # 重载Nginx
    log_info "重载Nginx..."
    sudo nginx -t && sudo systemctl reload nginx
    
    log_info "前端部署完成"
}

# ===========================================
# 健康检查
# ===========================================
health_check() {
    log_info "执行健康检查..."
    
    # 检查API健康
    API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    
    if [ "$API_HEALTH" == "200" ]; then
        log_info "API健康检查通过"
    else
        log_error "API健康检查失败: HTTP $API_HEALTH"
        exit 1
    fi
    
    # 检查前端
    FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
    
    if [ "$FRONTEND_HEALTH" == "200" ]; then
        log_info "前端健康检查通过"
    else
        log_warn "前端健康检查异常: HTTP $FRONTEND_HEALTH"
    fi
}

# ===========================================
# 回滚函数
# ===========================================
rollback() {
    log_warn "开始回滚..."
    
    # 找到最近的备份
    LATEST_BACKUP=$(ls -t $BACKUP_DIR/backup_*.tar.gz | head -1)
    
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "未找到备份文件"
        exit 1
    fi
    
    log_info "使用备份: $LATEST_BACKUP"
    
    # 解压备份
    tar -xzf $LATEST_BACKUP -C /tmp
    
    # 恢复数据库
    log_info "恢复数据库..."
    psql -U sales_user sales_db < /tmp/home/salesapp/backups/db_*.sql
    
    # 恢复配置
    log_info "恢复配置..."
    cp /tmp/home/salesapp/backups/env_* backend/.env
    
    # 回滚代码
    log_info "回滚代码..."
    git reset --hard HEAD~1
    
    # 重启服务
    sudo systemctl restart sales-app
    
    log_info "回滚完成"
}

# ===========================================
# 主流程
# ===========================================
main() {
    log_info "=========================================="
    log_info "开始部署 AI销售助手"
    log_info "时间: $(date)"
    log_info "=========================================="
    
    # 参数处理
    case "$1" in
        --rollback)
            rollback
            exit 0
            ;;
        --backend-only)
            check_services
            backup
            pull_code
            deploy_backend
            health_check
            ;;
        --frontend-only)
            pull_code
            deploy_frontend
            health_check
            ;;
        *)
            check_services
            backup
            pull_code
            deploy_backend
            deploy_frontend
            health_check
            ;;
    esac
    
    log_info "=========================================="
    log_info "部署完成！"
    log_info "=========================================="
}

# 执行主流程
main "$@"
