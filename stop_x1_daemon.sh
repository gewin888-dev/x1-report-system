#!/bin/bash
# X1 系统守护进程停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/daemon_common.sh"

write_section "stop_x1_daemon.sh"
capture_runtime_snapshot
capture_port_snapshot

if [ ! -f "$PID_FILE" ]; then
    if is_healthy; then
        write_event "X1 健康接口仍可访问，但 PID 文件不存在，需手动排查实际进程"
        exit 1
    fi
    LISTENER=$(port_listener_info)
    if [ -n "$LISTENER" ]; then
        write_event "端口 $APP_PORT 仍被其他进程占用，但 PID 文件不存在"
        print_port_diagnostics | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
        exit 1
    fi
    write_event "X1 服务未运行（PID 文件不存在）"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    write_event "X1 服务未运行（进程不存在）"
    rm -f "$PID_FILE"
    exit 0
fi

write_event "停止 X1 服务 (PID: $PID)..."
kill "$PID"

for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        write_event "✅ X1 服务已停止"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

write_event "强制停止 X1 服务..."
kill -9 "$PID" 2>/dev/null
rm -f "$PID_FILE"
write_event "✅ X1 服务已强制停止"
