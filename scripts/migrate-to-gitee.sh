#!/bin/bash
# 迁移到 Gitee 脚本

set -e

# 配置：请修改为您的 Gitee 仓库地址
GITEE_REPO_URL="${1:-}"

if [ -z "$GITEE_REPO_URL" ]; then
    echo "用法: $0 <gitee-repo-url>"
    echo "示例: $0 https://gitee.com/your-username/z-pulse.git"
    echo "  或: $0 git@gitee.com:your-username/z-pulse.git"
    exit 1
fi

echo "🔄 开始迁移到 Gitee..."
echo "仓库地址: $GITEE_REPO_URL"
echo ""

# 检查是否已有 gitee 远程
if git remote | grep -q "^gitee$"; then
    echo "⚠️  Gitee 远程已存在，更新中..."
    git remote set-url gitee "$GITEE_REPO_URL"
else
    echo "➕ 添加 Gitee 远程仓库..."
    git remote add gitee "$GITEE_REPO_URL"
fi

echo ""
echo "📋 当前远程仓库："
git remote -v
echo ""

read -p "确认推送到 Gitee? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "📤 推送 main 分支到 Gitee..."
git push gitee main || {
    echo "❌ 推送失败，请检查："
    echo "  1. Gitee 仓库地址是否正确"
    echo "  2. 是否已配置认证（SSH 密钥或访问令牌）"
    exit 1
}

echo ""
echo "📤 推送所有标签..."
git push gitee --tags 2>/dev/null || echo "没有标签需要推送"

echo ""
echo "📤 推送所有分支..."
git push gitee --all 2>/dev/null || echo "没有其他分支需要推送"

echo ""
echo "✅ 迁移完成！"
echo ""
echo "现在您可以使用以下命令："
echo "  - 推送到 Gitee: git push gitee main"
echo "  - 推送到 GitHub: git push origin main"
