#!/bin/bash
# ============================================================
# X1 自动备份脚本
# 每日凌晨 2:00 由 cron/launchd 自动执行
# ============================================================

set -euo pipefail

# --- 配置 ---
X1_DIR="/Users/fuwuqi/检测报告生成系统_X1"
BACKUP_DIR="/Users/fuwuqi/backups_x1"
RETENTION_DAYS=30          # 自动备份保留天数
MAX_BACKUPS=60             # 最大备份份数
DATE_TAG=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="X1_auto_${DATE_TAG}.tar.gz"
LOG_FILE="${X1_DIR}/logs/backup_${DATE_TAG}.log"

# --- 函数 ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# --- 准备 ---
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log "===== X1 自动备份开始 ====="
log "源目录: $X1_DIR"
log "目标: $BACKUP_DIR/$BACKUP_NAME"

# --- 备份内容 ---
# 包含: 数据库、配置、记录元数据、模板注册
# 排除: 报告产出文件（大文件）、日志、缓存、node_modules、.git
cd "$X1_DIR"

INCLUDE_PATHS=(
    "x1_data.db"
    "data/"
    "x1_config.json"
    "template_config.json"
    "template_registry.json"
    "template_semantic_mappings.json"
    "template_type_mappings.json"
    "feishu_config.json"
    "static/standards_ranges.json"
    "static/standards_domain_map.json"
    "static/standards_db.js"
    "records_x1/"
    "app_x1.py"
    "auth.py"
    "judgement_engine.py"
    "template_rules.py"
    "template_resources.py"
    "payload_normalizer.py"
    "clean_class_semantics.py"
    "report_context_builder.py"
    "monitor.py"
    "database.py"
    "customer_routes.py"
    "customer_admin_routes.py"
    "feishu_utils.py"
    "config_loader.py"
    "adapters/"
    "static/admin.js"
    "static/record.js"
    "static/record.css"
    "static/admin_customers.js"
    "static/admin_projects.js"
    "static/admin_stats.js"
    "static/customer.js"
    "static/x-model.js"
    "templates/"
    "requirements.txt"
    ".gitignore"
)

# 构建 tar 参数
TAR_ARGS=""
for p in "${INCLUDE_PATHS[@]}"; do
    if [ -e "$p" ]; then
        TAR_ARGS="$TAR_ARGS $p"
    fi
done

# 执行备份
if tar -czf "$BACKUP_DIR/$BACKUP_NAME" $TAR_ARGS 2>>"$LOG_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | awk '{print $1}')
    log "✅ 备份成功: $BACKUP_NAME ($BACKUP_SIZE)"
else
    log "❌ 备份失败!"
    exit 1
fi

# --- 清理旧备份 ---
log "清理 ${RETENTION_DAYS} 天前的自动备份..."
DELETED=0
find "$BACKUP_DIR" -name "X1_auto_*.tar.gz" -mtime +"$RETENTION_DAYS" -type f | while read f; do
    rm -f "$f"
    log "  删除: $(basename "$f")"
    DELETED=$((DELETED + 1))
done

# 超过最大份数时，删最旧的
CURRENT_COUNT=$(ls "$BACKUP_DIR"/X1_auto_*.tar.gz 2>/dev/null | wc -l)
if [ "$CURRENT_COUNT" -gt "$MAX_BACKUPS" ]; then
    EXCESS=$((CURRENT_COUNT - MAX_BACKUPS))
    log "超出最大备份数($MAX_BACKUPS)，删除最旧的 $EXCESS 份..."
    ls -t "$BACKUP_DIR"/X1_auto_*.tar.gz | tail -n "$EXCESS" | while read f; do
        rm -f "$f"
        log "  删除: $(basename "$f")"
    done
fi

# --- Git 快照（如果有 Git）---
if [ -d "$X1_DIR/.git" ]; then
    cd "$X1_DIR"
    if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
        log "Git: 无未提交变更"
    else
        log "Git: 检测到未提交变更，创建自动快照..."
        git add -A 2>/dev/null
        git commit -m "auto: 每日自动快照 ${DATE_TAG}" --allow-empty 2>/dev/null || true
        log "Git: 快照已创建"
    fi
fi

# --- 完成 ---
FINAL_COUNT=$(ls "$BACKUP_DIR"/X1_auto_*.tar.gz 2>/dev/null | wc -l)
log "===== 备份完成 ====="
log "当前自动备份: $FINAL_COUNT 份"
log "最新: $BACKUP_NAME"
