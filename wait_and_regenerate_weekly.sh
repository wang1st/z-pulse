#!/bin/bash

echo "=========================================="
echo "等待1月1日-1月5日晨报生成完成"
echo "=========================================="
echo ""

MAX_WAIT=1800  # 最多等待30分钟
INTERVAL=30    # 每30秒检查一次
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # 检查任务状态
    PENDING=$(docker exec zpulse-db psql -U zpulse -d zpulse -t -c "SELECT COUNT(*) FROM report_jobs WHERE job_type = 'REGENERATE_DAILY' AND target_date >= '2026-01-01' AND target_date <= '2026-01-05' AND created_at >= '2026-01-05 08:27:00' AND status = 'PENDING';" 2>&1 | tr -d ' ')
    RUNNING=$(docker exec zpulse-db psql -U zpulse -d zpulse -t -c "SELECT COUNT(*) FROM report_jobs WHERE job_type = 'REGENERATE_DAILY' AND target_date >= '2026-01-01' AND target_date <= '2026-01-05' AND created_at >= '2026-01-05 08:27:00' AND status = 'RUNNING';" 2>&1 | tr -d ' ')
    SUCCESS=$(docker exec zpulse-db psql -U zpulse -d zpulse -t -c "SELECT COUNT(*) FROM report_jobs WHERE job_type = 'REGENERATE_DAILY' AND target_date >= '2026-01-01' AND target_date <= '2026-01-05' AND created_at >= '2026-01-05 08:27:00' AND status = 'SUCCESS';" 2>&1 | tr -d ' ')
    
    # 检查已生成的报告
    REPORT_COUNT=$(docker exec zpulse-db psql -U zpulse -d zpulse -t -c "SELECT COUNT(*) FROM ai_generated_reports WHERE report_type = 'DAILY' AND report_date >= '2026-01-01' AND report_date <= '2026-01-05';" 2>&1 | tr -d ' ')
    
    echo "[$(date '+%H:%M:%S')] 等待中..."
    echo "  任务: 待处理=$PENDING, 运行中=$RUNNING, 成功=$SUCCESS"
    echo "  报告: $REPORT_COUNT/5 天已生成"
    
    if [ "$PENDING" = "0" ] && [ "$RUNNING" = "0" ] && [ "$REPORT_COUNT" = "5" ]; then
        echo ""
        echo "✅ 所有晨报已生成完成！"
        echo ""
        echo "=========================================="
        echo "重新生成周报"
        echo "=========================================="
        echo ""
        
        docker exec zpulse-api python3 -m app.tools.regenerate_weekly_for_this_monday
        
        echo ""
        echo "✅ 周报重新生成完成！"
        exit 0
    fi
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo ""
echo "⚠️  等待超时，但继续检查..."
echo ""
echo "请手动执行："
echo "  docker exec zpulse-api python3 -m app.tools.regenerate_weekly_for_this_monday"

