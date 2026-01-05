#!/bin/bash
# ============================================
# weRSS 批量触发全量抓取脚本
# 用于批量触发所有公众号的全量抓取（抓取10页）
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}weRSS 批量触发全量抓取脚本${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 配置
WERSS_URL="${WERSS_URL:-http://localhost:8080}"

# 从 .env 文件读取认证信息（如果存在）
if [ -f ".env" ]; then
    export $(grep -E '^WERSS_ADMIN_USERNAME=|^WERSS_ADMIN_PASSWORD=' .env | grep -v '^#' | xargs)
fi

WERSS_USERNAME="${WERSS_ADMIN_USERNAME:-admin}"
WERSS_PASSWORD="${WERSS_ADMIN_PASSWORD:-admin@123}"
START_PAGE=0
END_PAGE=10  # 抓取10页

# 检查 jq 是否安装（用于解析 JSON）
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}提示: 未安装 jq，将使用 Python 解析 JSON${NC}"
    USE_JQ=false
else
    USE_JQ=true
fi

# 登录获取 token
echo -e "${YELLOW}步骤 1: 登录 weRSS...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${WERSS_URL}/api/v1/wx/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${WERSS_USERNAME}&password=${WERSS_PASSWORD}")

if [ "$USE_JQ" = true ]; then
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.access_token // empty')
else
    TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('access_token', ''))" 2>/dev/null || echo "")
fi

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ 登录失败，请检查用户名和密码${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 登录成功${NC}"
echo ""

# 获取所有公众号列表
echo -e "${YELLOW}步骤 2: 获取公众号列表...${NC}"
FEEDS_RESPONSE=$(curl -s -X GET "${WERSS_URL}/api/v1/wx/mps?limit=1000" \
    -H "Authorization: Bearer ${TOKEN}")

if [ "$USE_JQ" = true ]; then
    FEED_COUNT=$(echo "$FEEDS_RESPONSE" | jq '.data.list | length')
    echo -e "${GREEN}✅ 找到 ${FEED_COUNT} 个公众号${NC}"
else
    FEED_COUNT=$(echo "$FEEDS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', {}).get('list', [])))" 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ 找到 ${FEED_COUNT} 个公众号${NC}"
fi

echo ""

# 批量触发抓取
echo -e "${YELLOW}步骤 3: 批量触发全量抓取（end_page=${END_PAGE}）...${NC}"
echo -e "${BLUE}注意: 每个公众号之间有 60 秒的防频繁更新限制${NC}"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

if [ "$USE_JQ" = true ]; then
    echo "$FEEDS_RESPONSE" | jq -r '.data.list[] | "\(.id)|\(.mp_name)"' | while IFS='|' read -r mp_id mp_name; do
        echo -e "${YELLOW}正在触发: ${mp_name} (${mp_id})...${NC}"
        
        UPDATE_RESPONSE=$(curl -s -X GET "${WERSS_URL}/api/v1/wx/mps/update/${mp_id}?start_page=${START_PAGE}&end_page=${END_PAGE}" \
            -H "Authorization: Bearer ${TOKEN}")
        
        ERROR_CODE=$(echo "$UPDATE_RESPONSE" | jq -r '.code // 0')
        
        if [ "$ERROR_CODE" = "40402" ]; then
            echo -e "${YELLOW}  ⚠️  跳过（频繁更新限制，需要等待）${NC}"
            SKIP_COUNT=$((SKIP_COUNT + 1))
        elif [ "$ERROR_CODE" = "0" ] || [ -z "$ERROR_CODE" ]; then
            echo -e "${GREEN}  ✅ 已触发${NC}"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            ERROR_MSG=$(echo "$UPDATE_RESPONSE" | jq -r '.message // "未知错误"')
            echo -e "${RED}  ❌ 失败: ${ERROR_MSG}${NC}"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        
        # 等待1秒，避免过快请求
        sleep 1
    done
else
    echo "$FEEDS_RESPONSE" | python3 << 'PYEOF'
import sys
import json
import time
import subprocess
import os

data = json.load(sys.stdin)
feeds = data.get('data', {}).get('list', [])

werss_url = os.getenv('WERSS_URL', 'http://localhost:8080')
token = os.getenv('TOKEN', '')
start_page = int(os.getenv('START_PAGE', '0'))
end_page = int(os.getenv('END_PAGE', '10'))

success_count = 0
fail_count = 0
skip_count = 0

for feed in feeds:
    mp_id = feed.get('id')
    mp_name = feed.get('mp_name', '未知')
    
    print(f"正在触发: {mp_name} ({mp_id})...", flush=True)
    
    # 调用 API
    import urllib.request
    import urllib.parse
    
    url = f"{werss_url}/api/v1/wx/mps/update/{mp_id}?start_page={start_page}&end_page={end_page}"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            code = result.get('code', 0)
            
            if code == 40402:
                print(f"  ⚠️  跳过（频繁更新限制，需要等待）", flush=True)
                skip_count += 1
            elif code == 0 or code is None:
                print(f"  ✅ 已触发", flush=True)
                success_count += 1
            else:
                msg = result.get('message', '未知错误')
                print(f"  ❌ 失败: {msg}", flush=True)
                fail_count += 1
    except Exception as e:
        print(f"  ❌ 错误: {e}", flush=True)
        fail_count += 1
    
    time.sleep(1)  # 等待1秒

print(f"\n完成: 成功 {success_count}, 失败 {fail_count}, 跳过 {skip_count}")
PYEOF
    TOKEN="$TOKEN" START_PAGE="$START_PAGE" END_PAGE="$END_PAGE" WERSS_URL="$WERSS_URL"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}批量触发完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "注意："
echo "  - 每个公众号有 60 秒的防频繁更新限制"
echo "  - 如果某些公众号被跳过，请等待 60 秒后重新运行脚本"
echo "  - 或者手动在 Web UI 中触发这些公众号的抓取"

