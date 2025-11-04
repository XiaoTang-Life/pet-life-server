#!/bin/bash
# 备选构建脚本 - 直接修改 requirements.txt 注入 token
#
# 如果 Install Command 方式不生效，可以使用此脚本
# 配置方式：在 Vercel 项目设置中设置 Build Command: bash build-alternative.sh

set -e

echo "🔧 配置 Git 认证并安装依赖..."

# 检查 GITHUB_TOKEN 环境变量
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 错误: 未设置 GITHUB_TOKEN 环境变量"
    exit 1
fi

# 备份原始 requirements.txt
cp requirements.txt requirements.txt.original

# 修改 requirements.txt，注入 token
echo "📝 更新 requirements.txt，注入 GitHub token..."
sed -i.tmp "s|git+https://github.com/DeeWooo/micro-life-sim.git|git+https://${GITHUB_TOKEN}@github.com/DeeWooo/micro-life-sim.git|g" requirements.txt

# 配置 Git credential helper（双重保险）
git config --global credential.helper store
mkdir -p ~/.git
echo "https://${GITHUB_TOKEN}@github.com" > ~/.git-credentials

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install -r requirements.txt

# 恢复原始 requirements.txt
mv requirements.txt.original requirements.txt
rm -f requirements.txt.tmp

echo "✅ 依赖安装完成"

