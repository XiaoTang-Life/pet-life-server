#!/bin/bash
# 构建准备脚本 - 配置 Git 认证并修改 requirements.txt
#
# 此脚本会在安装依赖前修改 requirements.txt，注入 GitHub token
# 然后安装依赖到 Vercel 指定的目录

set -e

echo "🔧 准备构建环境..."

# 检查 GITHUB_TOKEN 环境变量
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 错误: 未设置 GITHUB_TOKEN 环境变量"
    echo "请在 Vercel 项目设置中添加 GITHUB_TOKEN 环境变量"
    exit 1
fi

echo "✅ 检测到 GITHUB_TOKEN"

# 配置 Git credential helper
echo "🔐 配置 Git credential helper..."
git config --global credential.helper store
mkdir -p ~/.git
echo "https://${GITHUB_TOKEN}@github.com" > ~/.git-credentials

# 备份原始 requirements.txt
if [ ! -f requirements.txt.original ]; then
    cp requirements.txt requirements.txt.original
fi

# 修改 requirements.txt，注入 token
echo "📝 更新 requirements.txt，注入 GitHub token..."
sed -i.tmp "s|git+https://github.com/XiaoTang-Life/micro-life-sim.git|git+https://${GITHUB_TOKEN}@github.com/XiaoTang-Life/micro-life-sim.git|g" requirements.txt

# 修改 requirements.txt 后，让 Vercel 的 Python builder 继续安装
# 恢复原始 requirements.txt 将在构建完成后进行（如果需要）
# 注意：这里不恢复 requirements.txt，让 Vercel 使用修改后的版本

echo "✅ 构建环境准备完成"
echo "📦 requirements.txt 已更新，包含 GitHub token"
echo "   现在 Vercel Python builder 将使用更新后的 requirements.txt 安装依赖"

