#!/bin/bash

# 批量全量抓取所有公众号 12月31日后的文章
# 使用方法: ./scripts/batch-full-collect-after-dec31.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# weRSS 配置
WERSS_URL="${WERSS_URL:-http://localhost:8080}"
WERSS_USERNAME="${WERSS_USERNAME:-admin}"
WERSS_PASSWORD="${WERSS_PASSWORD:-admin@123}"

# 抓取配置
START_PAGE=0
END_PAGE=10  # 抓取前10页，覆盖12月31日后的文章

# 串行执行配置
SERIAL_MODE="${SERIAL_MODE:-true}"  # 是否串行执行（一个完成后再执行下一个），默认true
WAIT_TIME="${WAIT_TIME:-120}"  # 每个公众号抓取后等待的时间（秒），默认120秒，确保任务完成

echo "============================================================"
echo "批量全量抓取所有公众号 12月31日后的文章"
echo "============================================================"
echo ""

# 检查 jq 是否安装
if command -v jq &> /dev/null; then
    USE_JQ=true
else
    USE_JQ=false
    echo -e "${YELLOW}提示: 未安装 jq，将使用 Python 解析 JSON${NC}"
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
echo -e "${YELLOW}步骤 2: 获取所有公众号列表...${NC}"
MPS_RESPONSE=$(curl -s -X GET "${WERSS_URL}/api/v1/wx/mps?limit=100" \
    -H "Authorization: Bearer ${TOKEN}")

if [ "$USE_JQ" = true ]; then
    MP_COUNT=$(echo "$MPS_RESPONSE" | jq -r '.data.list | length // 0')
else
    MP_COUNT=$(echo "$MPS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', {}).get('list', [])))" 2>/dev/null || echo "0")
fi

if [ "$MP_COUNT" = "0" ] || [ -z "$MP_COUNT" ]; then
    echo -e "${RED}❌ 未找到公众号${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 找到 ${MP_COUNT} 个公众号${NC}"
echo ""

# 提取公众号列表
echo -e "${YELLOW}步骤 3: 开始批量触发全量抓取...${NC}"
echo "抓取配置: start_page=${START_PAGE}, end_page=${END_PAGE}"
echo "目标: 12月31日后的文章"
echo ""

# 使用 Python 处理，因为需要遍历列表
# 通过环境变量传递参数
export TOKEN
export WERSS_URL
export START_PAGE
export END_PAGE
export MPS_RESPONSE
export SERIAL_MODE
export WAIT_TIME

python3 << 'PYEOF'
# -*- coding: utf-8 -*-
import json
import sys
import time
import requests
import os

# 从环境变量获取参数
token = os.environ.get('TOKEN', '')
werss_url = os.environ.get('WERSS_URL', 'http://localhost:8080')
start_page = int(os.environ.get('START_PAGE', '0'))
end_page = int(os.environ.get('END_PAGE', '10'))
mps_response = os.environ.get('MPS_RESPONSE', '{}')

# 解析公众号列表
mps_data = json.loads(mps_response)
mps = mps_data.get('data', {}).get('list', [])

if not mps:
    print("❌ 未找到公众号")
    sys.exit(1)

print(f"✅ 找到 {len(mps)} 个公众号")
print()

# 获取执行模式配置
serial_mode = os.environ.get('SERIAL_MODE', 'true').lower() == 'true'
wait_time = int(os.environ.get('WAIT_TIME', '120'))

if serial_mode:
    print(f"执行模式: 串行执行（一个完成后再执行下一个）")
    print(f"等待时间: 每个公众号抓取后等待 {wait_time} 秒")
else:
    print(f"执行模式: 并发执行")
print()
print("开始批量触发全量抓取...")
print()

headers = {"Authorization": f"Bearer {token}"}

success_count = 0
skip_count = 0
failed_count = 0

for i, mp in enumerate(mps, 1):
    mp_id = mp.get('id', '')
    mp_name = mp.get('mp_name', '未知')
    
    if not mp_id:
        continue
    
    print(f"[{i}/{len(mps)}] 触发 {mp_name} (ID: {mp_id})...", end=" ")
    
    try:
        update_url = f"{werss_url}/api/v1/wx/mps/update/{mp_id}?start_page={start_page}&end_page={end_page}"
        response = requests.get(update_url, headers=headers, timeout=30)
        data = response.json()
        
        code = data.get("code", 0)
        if code == 40402:
            print("⚠️  跳过（频繁更新限制，请等待 60 秒后重试）")
            skip_count += 1
            if serial_mode:
                print(f"   等待 {wait_time} 秒后继续下一个...")
                time.sleep(wait_time)
            else:
                time.sleep(5)
        elif code == 0 or code is None:
            print("✅ 成功")
            success_count += 1
            
            # 串行模式：等待任务完成后再继续下一个
            if serial_mode:
                print(f"   等待 {wait_time} 秒，确保任务完成后再继续下一个...")
                time.sleep(wait_time)
        else:
            msg = data.get("message", "未知错误")
            print(f"❌ 失败: {msg}")
            failed_count += 1
            if serial_mode:
                time.sleep(10)  # 失败后也等待一下
    except requests.exceptions.Timeout:
        print("⏱️  超时（服务器可能正在处理其他任务）")
        failed_count += 1
        if serial_mode:
            print(f"   等待 {wait_time} 秒后继续下一个...")
            time.sleep(wait_time)
        else:
            time.sleep(5)
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            print("⏱️  超时（服务器可能正在处理其他任务）")
        else:
            print(f"❌ 错误: {error_msg}")
        failed_count += 1
        if serial_mode:
            time.sleep(10)  # 错误后也等待一下
        else:
            time.sleep(3)
    
    # 非串行模式：每个请求后都等待，避免过载
    if not serial_mode:
        if i % 5 == 0:
            time.sleep(3)
        else:
            time.sleep(1)  # 每个请求之间至少等待1秒

print()
print("=" * 60)
print("批量触发完成")
print("=" * 60)
print(f"✅ 成功: {success_count} 个")
print(f"⚠️  跳过: {skip_count} 个（频繁更新限制）")
print(f"❌ 失败: {failed_count} 个")
print()
print("💡 说明：")
print("  - 每个公众号有 60 秒的防频繁更新限制")
print("  - 抓取任务会在后台自动执行")
print("  - 可以通过日志查看抓取进度:")
print("    docker logs -f zpulse-rss | grep '📰 文章信息'")
print()
PYEOF

echo ""
echo "============================================================"
echo "任务已提交，weRSS 正在后台抓取文章"
echo "============================================================"

