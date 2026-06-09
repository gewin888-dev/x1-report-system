#!/bin/bash
# X1 系统守护进程启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/daemon_common.sh"

write_section "start_x1_daemon.sh"
capture_runtime_snapshot
capture_port_snapshot
capture_health_snapshot

if is_healthy; then
    if [ -f "$PID_FILE" ]; then
        RUN_PID=$(cat "$PID_FILE" 2>/dev/null)
        write_event "X1 服务已在运行 (PID: ${RUN_PID:-unknown})"
    else
        write_event "X1 服务已在运行（检测到健康接口正常，但 PID 文件缺失）"
        print_port_diagnostics | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
    fi
    exit 0
fi

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        write_event "检测到旧 PID 仍存在但健康接口未通过，先停止旧进程 (PID: $OLD_PID)"
        kill "$OLD_PID" 2>/dev/null || true
        sleep 2
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            write_event "旧进程未退出，执行强制停止"
            kill -9 "$OLD_PID" 2>/dev/null || true
            sleep 1
        fi
    fi
    write_event "清理旧的 PID 文件"
    rm -f "$PID_FILE"
fi

EXISTING_LISTENER=$(port_listener_info)
if [ -n "$EXISTING_LISTENER" ]; then
    write_event "❌ 端口 $APP_PORT 已被其他进程占用，X1 未启动"
    echo "$EXISTING_LISTENER" | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
    print_port_diagnostics | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
    write_event "请先释放端口后再启动"
    exit 1
fi

write_event "启动 X1 服务..."
cd "$SCRIPT_DIR"
write_start_banner
nohup env PYTHONPATH=/Users/fuwuqi/Library/Python/3.9/lib/python/site-packages \
  /Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python \
  -m waitress --host="$APP_HOST" --port="$APP_PORT" app_x1:app >> "$APP_LOG_FILE" 2>&1 &
PID=$!

echo $PID > "$PID_FILE"
write_event "X1 服务已启动 (PID: $PID)"
write_event "守护脚本日志: $TODAY_LOG_FILE"
write_event "应用日志: $APP_LOG_FILE"
write_event "人工运维日志: $MANUAL_RESTART_LOG"

for i in {1..10}; do
    if is_healthy; then
        write_event "✅ X1 服务运行正常"
        exit 0
    fi
    if ! ps -p "$PID" > /dev/null 2>&1; then
        write_event "❌ X1 进程已退出，启动失败"
        capture_app_log_tail
        rm -f "$PID_FILE"
        exit 1
    fi
    sleep 1
done

write_event "⚠️  X1 服务可能未正常启动"
capture_health_snapshot
capture_app_log_tail
exit 1
