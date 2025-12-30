#!/bin/bash
# 自动化脚本：监控晨报生成 -> 自动发送邮件

echo "=== 晨报生成与邮件发送自动化流程 ==="
echo ""
echo "📋 已创建任务："
echo "  • Job 68: 2025-12-15"
echo "  • Job 69: 2025-12-16"  
echo "  • Job 70: 2025-12-17"
echo "  • Job 71: 2025-12-18"
echo "  • Job 72: 2025-12-19"
echo "  • Job 73: 2025-12-20"
echo ""

# 持续监控任务状态
MAX_WAIT=3600  # 最多等待1小时
ELAPSED=0
CHECK_INTERVAL=30  # 每30秒检查一次

while [ $ELAPSED -lt $MAX_WAIT ]; do
    echo "⏰ [$(date +%H:%M:%S)] 检查任务进度..."
    
    # 检查任务状态
    docker cp /Users/ethan/Codes/z-pulse/check_status.py zpulse-ai-worker:/app/ > /dev/null 2>&1
    STATUS_OUTPUT=$(docker compose exec -T ai-worker python /app/check_status.py 2>/dev/null)
    echo "$STATUS_OUTPUT"
    
    # 提取成功数量
    SUCCESS_COUNT=$(echo "$STATUS_OUTPUT" | grep "完成率" | grep -oE "[0-9]+/6" | cut -d'/' -f1)
    
    if [ "$SUCCESS_COUNT" = "6" ]; then
        echo ""
        echo "✅ 所有晨报已生成完成！开始发送邮件..."
        echo ""
        
        # 复制并执行邮件发送脚本
        docker cp /Users/ethan/Codes/z-pulse/send_emails.py zpulse-ai-worker:/app/
        docker compose exec -T ai-worker python /app/send_emails.py
        
        echo ""
        echo "🎉 所有任务完成！"
        exit 0
    fi
    
    echo "⏳ 等待中... (已等待 ${ELAPSED}秒)"
    echo ""
    sleep $CHECK_INTERVAL
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))
done

echo "⏱️  超时：部分任务未完成"
echo "请手动检查任务状态"
exit 1
