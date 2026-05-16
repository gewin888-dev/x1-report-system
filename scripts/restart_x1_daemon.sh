#!/bin/bash
# X1 系统守护进程重启脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/daemon_common.sh"

write_section "restart_x1_daemon.sh"
capture_runtime_snapshot
capture_port_snapshot
capture_health_snapshot

write_event "开始执行 restart 流程"
"$SCRIPT_DIR/stop_x1_daemon.sh"
STOP_RC=$?
write_event "stop_x1_daemon.sh 退出码=$STOP_RC"

sleep 1

"$SCRIPT_DIR/start_x1_daemon.sh"
START_RC=$?
write_event "start_x1_daemon.sh 退出码=$START_RC"

capture_health_snapshot
capture_port_snapshot
capture_app_log_tail

if [ "$START_RC" -eq 0 ] && is_healthy; then
    write_event "✅ restart 完成，服务健康"
    print_restart_summary
    exit 0
fi

write_event "❌ restart 未完全成功，请查看日志：$MANUAL_RESTART_LOG"
print_restart_summary
exit 1
