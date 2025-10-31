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

# 检查 Python 版本（Vercel 使用 3.12）
PYTHON_VERSION="3.12"
echo "🐍 使用 Python 版本: ${PYTHON_VERSION}"

# 检测 Vercel 的项目结构（根据日志，安装目标是 api/_vendor）
if [ -d "api" ]; then
    INSTALL_TARGET=".vercel/python/py${PYTHON_VERSION}/api/_vendor"
else
    INSTALL_TARGET=".vercel/python/py${PYTHON_VERSION}/_vendor"
fi

echo "📦 安装依赖到: ${INSTALL_TARGET}"

# 创建目标目录（包括所有父目录）
mkdir -p "${INSTALL_TARGET}"

# 安装依赖（使用与 Vercel 完全相同的命令格式）
echo "📥 开始安装依赖..."
pip3.12 install --disable-pip-version-check --no-compile --no-cache-dir --target "${INSTALL_TARGET}" --upgrade -r requirements.txt 2>&1

INSTALL_STATUS=$?

if [ $INSTALL_STATUS -eq 0 ]; then
    echo "✅ 依赖安装成功"
    
    # 恢复原始 requirements.txt（保持仓库干净）
    mv requirements.txt.original requirements.txt
    rm -f requirements.txt.tmp
    
    echo "✅ 构建准备完成，依赖已安装到: ${INSTALL_TARGET}"
else
    echo "❌ 依赖安装失败，退出码: $INSTALL_STATUS"
    # 恢复原始 requirements.txt
    mv requirements.txt.original requirements.txt 2>/dev/null || true
    rm -f requirements.txt.tmp
    exit $INSTALL_STATUS
fi

