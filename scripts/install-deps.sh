#!/bin/bash
# 安装依赖脚本 - 配置 Git 认证以访问私有仓库
# 
# 使用方法：
# 1. 在 Vercel 项目设置中添加环境变量 GITHUB_TOKEN
# 2. 在 vercel.json 中配置构建命令使用此脚本
#
# 注意：此脚本会在安装前修改 requirements.txt，将 GitHub URL 替换为带 token 的版本

set -e

# 检查是否设置了 GITHUB_TOKEN
if [ -z "$GITHUB_TOKEN" ]; then
    echo "错误: 未设置 GITHUB_TOKEN 环境变量"
    echo "请在 Vercel 项目设置中添加 GITHUB_TOKEN 环境变量"
    echo "获取方式: GitHub Settings -> Developer settings -> Personal access tokens"
    exit 1
fi

echo "配置 Git 认证..."

# 配置 Git credential helper
git config --global credential.helper store
echo "https://${GITHUB_TOKEN}@github.com" > ~/.git-credentials

# 备份原始的 requirements.txt
cp requirements.txt requirements.txt.original

# 修改 requirements.txt 中的 GitHub URL，注入 token
# 将 git+https://github.com/... 替换为 git+https://TOKEN@github.com/...
sed -i.bak "s|git+https://github.com/DeeWooo/micro-life-sim.git|git+https://${GITHUB_TOKEN}@github.com/DeeWooo/micro-life-sim.git|g" requirements.txt

echo "开始安装依赖..."
pip install -r requirements.txt

# 恢复原始 requirements.txt（保持仓库干净）
mv requirements.txt.original requirements.txt
rm -f requirements.txt.bak

echo "✅ 依赖安装完成"

