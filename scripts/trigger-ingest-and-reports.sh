#!/bin/bash
# ============================================
# 触发 ingestion-worker 提取文章并生成报告
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}触发 ingestion-worker 并生成报告${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 配置
API_URL="${API_URL:-http://localhost:8000}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin@123}"

# 从 .env 文件读取配置（如果存在）
if [ -f ".env" ]; then
    export $(grep -E '^ADMIN_USERNAME=|^ADMIN_PASSWORD=|^API_URL=' .env | grep -v '^#' | xargs)
fi

echo -e "${YELLOW}步骤 1: 登录 API 获取 token...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/api/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${ADMIN_USERNAME}&password=${ADMIN_PASSWORD}")

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ 登录失败，请检查用户名和密码${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 登录成功${NC}"
echo ""

echo -e "${YELLOW}步骤 2: 触发 ingestion-worker 提取文章...${NC}"
COLLECT_RESPONSE=$(curl -s -X POST "${API_URL}/api/admin/articles/collect" \
    -H "Authorization: Bearer ${TOKEN}")

JOB_ID=$(echo "$COLLECT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('job_id', ''))" 2>/dev/null || echo "")

if [ -z "$JOB_ID" ]; then
    echo -e "${RED}❌ 触发失败${NC}"
    echo "响应: $COLLECT_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ 已触发采集任务 (Job ID: ${JOB_ID})${NC}"
echo ""

echo -e "${YELLOW}步骤 3: 等待 ingestion-worker 完成...${NC}"
echo "正在监控任务状态..."

MAX_WAIT=1800  # 最多等待30分钟
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS_RESPONSE=$(curl -s -X GET "${API_URL}/api/admin/articles/collect/status?job_id=${JOB_ID}" \
        -H "Authorization: Bearer ${TOKEN}")
    
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    
    if [ "$STATUS" = "success" ] || [ "$STATUS" = "SUCCESS" ]; then
        echo -e "${GREEN}✅ ingestion-worker 已完成${NC}"
        NEW_ARTICLES=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('new_articles', 0))" 2>/dev/null || echo "0")
        echo "  新提取文章数: ${NEW_ARTICLES}"
        break
    elif [ "$STATUS" = "failed" ] || [ "$STATUS" = "FAILED" ]; then
        echo -e "${RED}❌ ingestion-worker 失败${NC}"
        exit 1
    else
        echo "  状态: ${STATUS} (已等待 ${ELAPSED} 秒)"
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}⚠️  等待超时，但继续执行报告生成${NC}"
fi

echo ""

echo -e "${YELLOW}步骤 4: 生成 1月2日的晨报...${NC}"
REPORT1_RESPONSE=$(curl -s -X POST "${API_URL}/api/admin/reports/generate" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"date": "2026-01-02", "report_type": "daily"}')

REPORT1_ID=$(echo "$REPORT1_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$REPORT1_ID" ]; then
    echo -e "${GREEN}✅ 已生成 1月2日晨报 (ID: ${REPORT1_ID})${NC}"
else
    echo -e "${YELLOW}⚠️  生成 1月2日晨报失败或已存在${NC}"
    echo "响应: $REPORT1_RESPONSE"
fi

echo ""

echo -e "${YELLOW}步骤 5: 生成 1月3日的晨报...${NC}"
REPORT2_RESPONSE=$(curl -s -X POST "${API_URL}/api/admin/reports/generate" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"date": "2026-01-03", "report_type": "daily"}')

REPORT2_ID=$(echo "$REPORT2_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$REPORT2_ID" ]; then
    echo -e "${GREEN}✅ 已生成 1月3日晨报 (ID: ${REPORT2_ID})${NC}"
else
    echo -e "${YELLOW}⚠️  生成 1月3日晨报失败或已存在${NC}"
    echo "响应: $REPORT2_RESPONSE"
fi

echo ""

echo -e "${YELLOW}步骤 6: 发送报告给订阅用户...${NC}"
# 报告生成后会自动发送，这里只是确认
echo -e "${GREEN}✅ 报告已生成，系统会自动发送给订阅用户${NC}"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}完成！${NC}"
echo -e "${GREEN}============================================${NC}"

