#!/bin/bash
# X1 系统最小回归测试清单
# 基于 2026-04-29 的 9/9 全通过基线

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPT="/Users/fuwuqi/检测报告生成系统_X1/test_x1_objects_auth.py"

echo "==================================="
echo "X1 系统回归测试"
echo "==================================="
echo ""

# 检查服务状态
echo "1. 检查服务状态..."
if ! curl -s http://localhost:8082/api/x/health | grep -q '"success":true'; then
    echo "❌ X1 服务未运行或异常"
    echo "请先启动服务: ./start_x1_daemon.sh"
    exit 1
fi
echo "✅ X1 服务运行正常"
echo ""

# 运行主测试套件
echo "2. 运行对象导出测试（9个核心对象）..."
if [ -f "$TEST_SCRIPT" ]; then
    LOG_FILE="/tmp/x1_regression_$(date +%Y%m%d_%H%M%S).log"
    python3 "$TEST_SCRIPT" 2>&1 | tee "$LOG_FILE"
    
    # 检查结果
    if grep -q "🎉 所有对象测试通过" "$LOG_FILE"; then
        echo ""
        echo "✅ 回归测试通过"
        exit 0
    else
        echo ""
        echo "❌ 回归测试失败，请检查日志"
        exit 1
    fi
else
    echo "⚠️  测试脚本不存在: $TEST_SCRIPT"
    echo "请确保测试脚本已部署"
    exit 1
fi
