#!/bin/bash
#
# 设置WeRSS Token监控定时任务
# 每天早上9点检查一次token状态
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKER_SCRIPT="$SCRIPT_DIR/../workers/werss_token_monitor.py"

echo "=========================================="
echo "WeRSS Token Monitor Cron Setup"
echo "=========================================="

# 检查worker脚本是否存在
if [ ! -f "$WORKER_SCRIPT" ]; then
    echo "❌ Error: Worker script not found at $WORKER_SCRIPT"
    exit 1
fi

# 获取Python路径
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Error: python3 not found in PATH"
    exit 1
fi

# 显示即将添加的cron任务
echo ""
echo "即将添加的定时任务："
echo "每天早上9:00执行token监控检查"
echo ""
echo "Cron表达式："
echo "0 9 * * * $PYTHON_PATH $WORKER_SCRIPT --once >> /var/log/werss_monitor.log 2>&1"
echo ""

# 询问是否确认
read -p "是否确认添加？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 0
fi

# 添加到crontab
(crontab -l 2>/dev/null | grep -v "werss_token_monitor"; echo "0 9 * * * $PYTHON_PATH $WORKER_SCRIPT --once >> /var/log/werss_monitor.log 2>&1") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 定时任务设置成功！"
    echo ""
    echo "当前crontab内容："
    crontab -l | grep werss
    echo ""
    echo "日志文件：/var/log/werss_monitor.log"
    echo ""
    echo "如需手动运行测试："
    echo "  $PYTHON_PATH $WORKER_SCRIPT --once"
    echo ""
else
    echo "❌ 设置失败，请检查是否有crontab权限"
    exit 1
fi
