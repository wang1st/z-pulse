#!/bin/bash

# 获取 we-mp-rss Feed ID 的脚本

echo "🔍 正在获取 we-mp-rss 订阅列表..."
echo ""

# 检查服务是否运行
if ! docker compose ps rss-bridge | grep -q "Up"; then
    echo "❌ we-mp-rss 服务未运行"
    echo "请先启动服务: docker compose up -d rss-bridge"
    exit 1
fi

# 尝试通过 API 获取订阅列表
echo "📡 通过 API 获取订阅列表..."
echo ""

FEEDS=$(curl -s http://localhost:8080/api/feeds 2>/dev/null)

if [ -z "$FEEDS" ] || [ "$FEEDS" = "null" ]; then
    echo "⚠️  当前没有订阅，或 API 返回为空"
    echo ""
    echo "💡 解决方案："
    echo "1. 访问 we-mp-rss Web UI: http://localhost:3001"
    echo "2. 如果 Web UI 无法访问，尝试："
    echo "   - 重启服务: docker compose restart rss-bridge"
    echo "   - 等待服务完全启动（可能需要1-2分钟）"
    echo "   - 检查日志: docker compose logs rss-bridge"
    echo ""
    echo "3. 或者直接通过 API 添加订阅（如果支持）"
    exit 0
fi

# 解析并显示 Feed ID
echo "✅ 找到以下订阅："
echo ""
echo "$FEEDS" | python3 -c "
import json
import sys

try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for i, feed in enumerate(data, 1):
            feed_id = feed.get('id') or feed.get('feed_id') or feed.get('_id', 'N/A')
            name = feed.get('name') or feed.get('title') or feed.get('wechat_name', 'N/A')
            wechat_id = feed.get('wechat_id') or feed.get('biz', 'N/A')
            print(f'{i}. {name}')
            print(f'   Feed ID: {feed_id}')
            print(f'   微信号: {wechat_id}')
            print(f'   RSS URL: http://localhost:8080/rss/{feed_id}')
            print('')
    elif isinstance(data, dict):
        # 单个订阅
        feed_id = data.get('id') or data.get('feed_id') or data.get('_id', 'N/A')
        name = data.get('name') or data.get('title') or data.get('wechat_name', 'N/A')
        wechat_id = data.get('wechat_id') or data.get('biz', 'N/A')
        print(f'订阅名称: {name}')
        print(f'Feed ID: {feed_id}')
        print(f'微信号: {wechat_id}')
        print(f'RSS URL: http://localhost:8080/rss/{feed_id}')
    else:
        print('无法解析返回数据')
        print('原始数据:', data)
except Exception as e:
    print(f'解析错误: {e}')
    print('原始数据:')
    print(sys.stdin.read())
" 2>/dev/null || echo "$FEEDS"

echo ""
echo "💡 使用说明："
echo "1. 复制上面的 Feed ID"
echo "2. 在 Z-Pulse 管理后台的 'we-mp-rss Feed ID' 字段中填写"
echo "3. 或者在导入模板文件的 werss_feed_id 列中填写"

