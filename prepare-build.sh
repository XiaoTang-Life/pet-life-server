#!/bin/bash
# 构建准备脚本 - 配置 Git 认证并修改 requirements.txt
#
# 此脚本会在安装依赖前修改 requirements.txt，注入 GitHub token
# 然后安装依赖，最后让 Vercel 的 Python builder 继续构建

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

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "🐍 检测到 Python 版本: ${PYTHON_VERSION}"

# 确定安装目标目录（Vercel 使用的目录）
INSTALL_TARGET="${VERCEL_PYTHON_VENDOR_PATH:-.vercel/python/py${PYTHON_VERSION}/_vendor}"
echo "📦 安装依赖到: ${INSTALL_TARGET}"

# 创建目标目录
mkdir -p "${INSTALL_TARGET}"

# 安装依赖（使用与 Vercel 相同的命令格式）
echo "📥 开始安装依赖..."
pip3 install --disable-pip-version-check --no-compile --no-cache-dir --target "${INSTALL_TARGET}" --upgrade -r requirements.txt || {
    echo "⚠️ pip3 失败，尝试使用 pip..."
    pip install --disable-pip-version-check --no-compile --no-cache-dir --target "${INSTALL_TARGET}" --upgrade -r requirements.txt
}

echo "✅ 依赖安装完成"

# 恢复原始 requirements.txt（保持仓库干净）
mv requirements.txt.original requirements.txt
rm -f requirements.txt.tmp

echo "✅ 构建准备完成，继续 Vercel 构建流程..."

