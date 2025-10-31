#!/bin/bash
# Vercel 构建脚本 - 配置 Git 认证以访问私有 GitHub 仓库
#
# 使用方法：
# 1. 在 Vercel 项目设置中添加环境变量 GITHUB_TOKEN
# 2. 在 Vercel 项目设置中配置 Install Command: bash build.sh
#    或者 Build Command: bash build.sh && vercel-build
#
# 注意：此脚本会配置 Git credential helper，让 pip 能够访问私有仓库

set -e

echo "🔧 配置 Git 认证以访问私有 GitHub 仓库..."

# 检查 GITHUB_TOKEN 环境变量
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 错误: 未设置 GITHUB_TOKEN 环境变量"
    echo ""
    echo "配置步骤："
    echo "1. 访问 https://github.com/settings/tokens"
    echo "2. 点击 'Generate new token (classic)'"
    echo "3. 权限至少勾选 'repo' (访问私有仓库)"
    echo "4. 生成后复制 token"
    echo "5. 在 Vercel 项目设置 -> Environment Variables 中添加："
    echo "   名称: GITHUB_TOKEN"
    echo "   值: <你的 GitHub token>"
    exit 1
fi

echo "✅ 检测到 GITHUB_TOKEN 环境变量"

# 配置 Git credential helper
# 这样 Git 在访问 GitHub 时会自动使用 token
echo "🔐 配置 Git credential helper..."
git config --global credential.helper store
mkdir -p ~/.git
echo "https://${GITHUB_TOKEN}@github.com" > ~/.git-credentials

# 验证 Git 配置
echo "📋 Git 配置信息："
git config --global --get credential.helper || echo "警告: credential helper 配置可能失败"

echo "✅ Git 认证配置完成"
echo ""
echo "📦 现在可以安全地安装依赖了"
echo "   Vercel 的 Python builder 会自动运行: pip install -r requirements.txt"
echo "   pip 在克隆 GitHub 仓库时会自动使用配置的 token"

