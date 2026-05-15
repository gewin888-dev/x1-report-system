#!/bin/bash
# X1 系统健康体检脚本（只读诊断，不做启停）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/daemon_common.sh"

echo "┌─────────────────────────────────────────────┐"
echo "│          X1 健康体检报告                    │"
echo "├─────────────────────────────────────────────┤"

# 1. PID 状态
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        printf "│ %-43s │\n" "PID 文件: ✅ $PID (存活)"
        printf "│ %-43s │\n" "启动时间: $(ps -p "$PID" -o lstart= 2>/dev/null)"
        printf "│ %-43s │\n" "内存: $(ps -p "$PID" -o rss= 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')"
    else
        printf "│ %-43s │\n" "PID 文件: ❌ $PID (已死亡)"
    fi
else
    printf "│ %-43s │\n" "PID 文件: ⚠️  不存在"
fi

# 2. 健康检查
if is_healthy; then
    printf "│ %-43s │\n" "健康接口: ✅ PASS"
else
    printf "│ %-43s │\n" "健康接口: ❌ FAIL"
fi

# 3. 端口监听
LISTENER=$(port_listener_info)
if [ -n "$LISTENER" ]; then
    LPID=$(echo "$LISTENER" | awk 'NR==1{print $2}')
    LCOMM=$(process_comm "$LPID" 2>/dev/null)
    LUSER=$(process_user "$LPID" 2>/dev/null)
    printf "│ %-43s │\n" "端口 8082: ✅ PID=$LPID ($LCOMM)"
    printf "│ %-43s │\n" "监听用户: $LUSER"
else
    printf "│ %-43s │\n" "端口 8082: ❌ 无监听者"
fi

# 4. 页面可达
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$APP_PORT/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    printf "│ %-43s │\n" "首页可达: ✅ HTTP $HTTP_CODE"
else
    printf "│ %-43s │\n" "首页可达: ❌ HTTP $HTTP_CODE"
fi

# 5. 日志文件
echo "├─────────────────────────────────────────────┤"
printf "│ %-43s │\n" "守护日志: $TODAY_LOG_FILE"
printf "│ %-43s │\n" "应用日志: $APP_LOG_FILE"

LATEST_MANUAL=$(ls -t "$APP_LOG_DIR"/manual_restart_*.log 2>/dev/null | head -1)
if [ -n "$LATEST_MANUAL" ]; then
    printf "│ %-43s │\n" "最近诊断: $(basename "$LATEST_MANUAL")"
else
    printf "│ %-43s │\n" "最近诊断: (无)"
fi

# 6. 磁盘占用
LOGS_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | awk '{print $1}')
APP_LOGS_SIZE=$(du -sh "$APP_LOG_DIR" 2>/dev/null | awk '{print $1}')
printf "│ %-43s │\n" "logs/ 大小: ${LOGS_SIZE:-N/A}"
printf "│ %-43s │\n" "logs_x1/ 大小: ${APP_LOGS_SIZE:-N/A}"

echo "└─────────────────────────────────────────────┘"

# 7. 最近应用日志异常痕迹
echo ""
echo "=== 最近应用日志异常痕迹 ==="
if [ -f "$APP_LOG_FILE" ]; then
    grep -i -E "error|traceback|exception|address already|failed|critical" "$APP_LOG_FILE" | tail -10
    ERRCNT=$(grep -ic -E "error|traceback|exception|address already|failed|critical" "$APP_LOG_FILE" 2>/dev/null || echo 0)
    echo "(共 $ERRCNT 条异常痕迹)"
else
    echo "(应用日志不存在)"
fi

# 8. 综合结论
echo ""
PID_OK=0; HEALTH_OK=0; PORT_OK=0; PAGE_OK=0
[ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" > /dev/null 2>&1 && PID_OK=1
is_healthy && HEALTH_OK=1
[ -n "$LISTENER" ] && PORT_OK=1
([ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]) && PAGE_OK=1

SCORE=$((PID_OK + HEALTH_OK + PORT_OK + PAGE_OK))
case $SCORE in
    4) echo "综合结论: ✅ 全部正常 (4/4)" ;;
    3) echo "综合结论: ⚠️  基本正常，有 1 项异常 (3/4)" ;;
    2) echo "综合结论: ⚠️  部分异常 (2/4)，建议重启" ;;
    *) echo "综合结论: ❌ 服务异常 ($SCORE/4)，建议立即排查" ;;
esac
