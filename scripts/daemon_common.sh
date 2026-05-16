#!/bin/bash
# X1 系统守护进程运维公共函数

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
APP_LOG_DIR="$SCRIPT_DIR/logs_x1"
PID_FILE="$SCRIPT_DIR/x1.pid"
APP_PORT=8082
HEALTH_URL="http://127.0.0.1:${APP_PORT}/api/x/health"
TODAY_LOG_FILE="$LOG_DIR/x1_$(date +%Y%m%d).log"
APP_LOG_FILE="$APP_LOG_DIR/app_$(date +%Y%m%d).log"
MANUAL_RESTART_LOG="$APP_LOG_DIR/manual_restart_$(date +%Y%m%d_%H%M%S).log"
START_TIMESTAMP="$(date '+%F %T')"

mkdir -p "$LOG_DIR" "$APP_LOG_DIR"

is_healthy() {
    curl -fsS "$HEALTH_URL" 2>/dev/null | grep -q '"success":true'
}

port_listener_raw() {
    lsof -nP -iTCP:"$APP_PORT" -sTCP:LISTEN 2>/dev/null
}

port_listener_info() {
    port_listener_raw | tail -n +2
}

port_listener_pids() {
    port_listener_info | awk '{print $2}' | sort -u
}

process_cmdline() {
    local pid="$1"
    ps -p "$pid" -o command= 2>/dev/null
}

process_comm() {
    local pid="$1"
    ps -p "$pid" -o comm= 2>/dev/null
}

process_user() {
    local pid="$1"
    ps -p "$pid" -o user= 2>/dev/null
}

print_port_diagnostics() {
    local found=0
    while IFS= read -r pid; do
        [ -z "$pid" ] && continue
        found=1
        local user comm cmd
        user=$(process_user "$pid")
        comm=$(process_comm "$pid")
        cmd=$(process_cmdline "$pid")
        echo "PID=$pid USER=${user:-unknown} COMM=${comm:-unknown}"
        echo "CMD=${cmd:-unknown}"
    done < <(port_listener_pids)

    if [ "$found" -eq 0 ]; then
        echo "(无端口占用者)"
    fi
}

write_event() {
    local message="$1"
    echo "[$(date '+%F %T')] $message" | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
}

write_section() {
    local title="$1"
    {
        echo ""
        echo "===== $title ====="
    } | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
}

capture_runtime_snapshot() {
    write_section "运行态快照"
    write_event "SCRIPT_DIR=$SCRIPT_DIR"
    write_event "PID_FILE=$PID_FILE"
    write_event "APP_PORT=$APP_PORT"
    if [ -f "$PID_FILE" ]; then
        write_event "PID_FILE_CONTENT=$(cat "$PID_FILE" 2>/dev/null)"
    else
        write_event "PID_FILE_CONTENT=(missing)"
    fi
    write_event "HEALTH_URL=$HEALTH_URL"
    write_event "TODAY_LOG_FILE=$TODAY_LOG_FILE"
    write_event "APP_LOG_FILE=$APP_LOG_FILE"
}

capture_port_snapshot() {
    write_section "端口占用快照"
    local raw
    raw=$(port_listener_info)
    if [ -n "$raw" ]; then
        echo "$raw" | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
        print_port_diagnostics | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
    else
        write_event "8082 当前无监听者"
    fi
}

capture_health_snapshot() {
    write_section "健康检查快照"
    if is_healthy; then
        write_event "health=PASS"
    else
        write_event "health=FAIL"
    fi
}

capture_app_log_tail() {
    write_section "应用日志尾部"
    if [ -f "$APP_LOG_FILE" ]; then
        tail -20 "$APP_LOG_FILE" | tee -a "$TODAY_LOG_FILE" "$MANUAL_RESTART_LOG"
    else
        write_event "应用日志不存在: $APP_LOG_FILE"
    fi
}

write_start_banner() {
    local banner="
================================================================================
  X1 SERVICE START — $START_TIMESTAMP
  PID_FILE: $PID_FILE
  APP_LOG: $APP_LOG_FILE
================================================================================"
    echo "$banner" >> "$APP_LOG_FILE"
}

print_restart_summary() {
    local pid=""
    [ -f "$PID_FILE" ] && pid=$(cat "$PID_FILE" 2>/dev/null)
    local health="FAIL"
    is_healthy && health="PASS"
    local listener
    listener=$(port_listener_info)

    echo ""
    echo "┌─────────────────────────────────────────────┐"
    echo "│          X1 RESTART 结果摘要                │"
    echo "├─────────────────────────────────────────────┤"
    printf "│ %-43s │\n" "时间: $START_TIMESTAMP"
    printf "│ %-43s │\n" "PID:  ${pid:-N/A}"
    printf "│ %-43s │\n" "健康: $health"
    if [ -n "$listener" ]; then
        local lpid lcomm
        lpid=$(echo "$listener" | awk 'NR==1{print $2}')
        lcomm=$(process_comm "$lpid" 2>/dev/null)
        printf "│ %-43s │\n" "端口: 8082 → PID=$lpid ($lcomm)"
    else
        printf "│ %-43s │\n" "端口: 8082 未监听"
    fi
    printf "│ %-43s │\n" "守护日志: $TODAY_LOG_FILE"
    printf "│ %-43s │\n" "应用日志: $APP_LOG_FILE"
    printf "│ %-43s │\n" "诊断日志: $MANUAL_RESTART_LOG"
    echo "└─────────────────────────────────────────────┘"
}
