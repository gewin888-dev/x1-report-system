#!/bin/bash
# X1 系统守护进程状态检查脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/daemon_common.sh"

write_section "status_x1_daemon.sh"
capture_runtime_snapshot
capture_port_snapshot

echo "=== X1 服务状态 ==="

LISTENER=$(port_listener_info)

if [ ! -f "$PID_FILE" ]; then
    if is_healthy; then
        echo "状态: ⚠️  服务健康运行，但 PID 文件不存在"
    elif [ -n "$LISTENER" ]; then
        echo "状态: ⚠️  端口 $APP_PORT 被占用，但健康接口未通过"
        print_port_diagnostics
    else
        echo "状态: ❌ 未运行（PID 文件不存在）"
    fi
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "状态: ❌ 未运行（进程不存在）"
    if is_healthy; then
        echo "提示: 健康接口正常，说明服务可能由其他进程接管，建议重建 PID 文件"
    elif [ -n "$LISTENER" ]; then
        echo "提示: 端口 $APP_PORT 当前被其他进程占用，X1 本体未持有该端口"
        print_port_diagnostics
    else
        echo "PID 文件存在但进程已终止，建议运行 stop_x1_daemon.sh 清理"
    fi
    exit 1
fi

echo "状态: ✅ 进程存在"
echo "PID: $PID"
echo "启动时间: $(ps -p "$PID" -o lstart=)"
echo "内存使用: $(ps -p "$PID" -o rss= | awk '{printf "%.1f MB", $1/1024}')"

if is_healthy; then
    echo "健康检查: ✅ 正常"
else
    echo "健康检查: ❌ 异常（进程存在但接口未通过）"
    if [ -n "$LISTENER" ]; then
        echo "端口监听:"
        print_port_diagnostics
    fi
fi

if [ -f "$TODAY_LOG_FILE" ]; then
    echo ""
    echo "=== 守护脚本日志（最后10行）==="
    tail -10 "$TODAY_LOG_FILE"
fi

if [ -f "$APP_LOG_FILE" ]; then
    echo ""
    echo "=== 应用日志（最后10行）==="
    tail -10 "$APP_LOG_FILE"
fi
