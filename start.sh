#!/bin/bash
# AAM 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    echo "AAM 启动脚本"
    echo ""
    echo "用法："
    echo "  $0 start        - 启动服务"
    echo "  $0 stop         - 停止服务"
    echo "  $0 restart      - 重启服务"
    echo "  $0 status       - 查看状态"
    echo "  $0 logs         - 查看日志"
    echo "  $0 help         - 显示帮助"
    echo ""
}

start() {
    echo -e "${GREEN}启动 AAM 服务...${NC}"
    
    # 检查 Python 虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 初始化数据库（如果不存在）
    if [ ! -f "logs/app.log" ]; then
        echo -e "${YELLOW}首次启动，初始化数据库...${NC}"
        python init_db.py
    fi
    
    # 启动服务
    nohup uvicorn app.api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        > logs/server.log \
        2>&1 &
    
    echo -e "${GREEN}服务启动成功${NC}"
    echo "访问：http://localhost:8000"
    echo "API 文档：http://localhost:8000/docs"
}

stop() {
    echo -e "${YELLOW}停止 AAM 服务...${NC}"
    
    # 查找进程并停止
    PID=$(ps aux | grep "[u]vicorn app.api.main" | awk '{print $2}')
    if [ -n "$PID" ]; then
        kill $PID
        echo -e "${GREEN}服务已停止${NC}"
    else
        echo -e "${RED}服务未运行${NC}"
    fi
}

restart() {
    stop
    sleep 2
    start
}

status() {
    echo "服务状态:"
    if ps aux | grep "[u]vicorn app.api.main" > /dev/null; then
        echo -e "${GREEN} 运行中${NC}"
        PID=$(ps aux | grep "[u]vicorn app.api.main" | awk '{print $2}')
        echo "PID: $PID"
    else
        echo -e "${RED} 未运行${NC}"
    fi
}

logs() {
    echo "服务日志:"
    tail -f logs/server.log
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
