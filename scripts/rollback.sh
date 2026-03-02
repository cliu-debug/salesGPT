#!/bin/bash

# ===========================================
# 数据库迁移回滚脚本
# ===========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

PROJECT_DIR="/home/salesapp/opc"

cd $PROJECT_DIR/backend

# 激活虚拟环境
source venv/bin/activate

# 显示当前版本
log_info "当前数据库版本:"
alembic current

# 显示迁移历史
log_info "迁移历史:"
alembic history --verbose

# 询问回滚步数
read -p "请输入回滚步数 (默认1): " STEPS
STEPS=${STEPS:-1}

log_warn "即将回滚 $STEPS 步"
read -p "确认回滚？(y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "回滚已取消"
    exit 0
fi

# 执行回滚
log_info "执行回滚..."
alembic downgrade -$STEPS

# 验证
log_info "回滚后版本:"
alembic current

log_info "回滚完成"
