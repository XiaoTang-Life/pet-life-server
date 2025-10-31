# Vercel 部署配置指南 - 私有 GitHub 仓库依赖

## 问题说明

`pet-life-server` 依赖私有 GitHub 仓库 `micro-life-sim`，需要在 Vercel 构建时配置 Git 认证。

## 解决方案

使用 GitHub Personal Access Token (PAT) 配置 Git 认证，让 Vercel 构建时能够访问私有仓库。

## 配置步骤

### 1. 创建 GitHub Personal Access Token

1. 访问：https://github.com/settings/tokens
2. 点击 **"Generate new token"** → **"Generate new token (classic)"**
3. 填写 Token 名称（如：`vercel-build-token`）
4. 选择过期时间（建议选择较长的时间，如 90 天或 1 年）
5. **重要：勾选权限 `repo`**（完整仓库访问权限，包括私有仓库）
6. 点击 **"Generate token"**
7. **立即复制 token**（只显示一次！）

### 2. 在 Vercel 项目中配置环境变量

1. 访问你的 Vercel 项目设置
2. 进入 **Settings** → **Environment Variables**
3. 添加新环境变量：
   - **Name**: `GITHUB_TOKEN`
   - **Value**: 粘贴刚才复制的 GitHub token
   - **Environment**: 选择所有环境（Production, Preview, Development）
4. 点击 **Save**

### 3. 配置 Vercel 安装命令（重要！）

**关键步骤**：需要在 **Install Command** 中运行构建脚本，而不是 Build Command。

#### 推荐方式：在 Vercel 项目设置中配置 Install Command

1. 进入 Vercel 项目：**Settings** → **General** → **Build & Development Settings**
2. 找到 **Install Command** 字段（不是 Build Command！）
3. 输入：`bash build.sh`
4. 保存设置

**为什么使用 Install Command？**
- Install Command 会在 `pip install -r requirements.txt` **之前**运行
- 这样 Git 认证会在安装依赖前配置好
- Build Command 会在 Python builder 运行**之后**执行，太晚了

#### 备选方式：如果 Install Command 不可用

如果 Vercel 项目设置中没有 Install Command 选项，可以尝试：

1. 使用 **Build Command**：`bash build.sh`
2. 但这样可能需要确保 Vercel 的 Python builder 仍然会运行 `pip install`

**注意**：如果使用 Build Command，可能需要确保不会覆盖 Vercel 的默认构建流程。

### 4. 验证配置

1. 提交代码到 GitHub
2. Vercel 会自动触发构建
3. 查看构建日志，应该看到：
   ```
   🔧 配置 Git 认证以访问私有 GitHub 仓库...
   ✅ 检测到 GITHUB_TOKEN 环境变量
   🔐 配置 Git credential helper...
   📋 Git 配置信息：store
   ✅ Git 认证配置完成
   
   📦 现在可以安全地安装依赖了
      Vercel 的 Python builder 会自动运行: pip install -r requirements.txt
      pip 在克隆 GitHub 仓库时会自动使用配置的 token
   ```
   
   然后应该看到 pip 成功克隆 `micro-life-sim` 仓库，而不是认证错误。
4. 如果看到错误信息，检查：
   - GITHUB_TOKEN 环境变量是否正确设置
   - Token 是否有 `repo` 权限
   - Token 是否已过期

## 工作原理

1. `build.sh` 脚本在构建开始时运行
2. 脚本读取 `GITHUB_TOKEN` 环境变量
3. 配置 Git credential helper，让 Git 自动使用 token
4. Vercel 的 Python builder 自动运行 `pip install -r requirements.txt`
5. pip 在克隆 GitHub 仓库时，Git 会自动使用配置的 token

## 安全注意事项

- ✅ **GitHub token 存储在 Vercel 环境变量中**，不会暴露在代码中
- ✅ **requirements.txt 保持不变**，不包含敏感信息
- ✅ **Token 只在构建时使用**，不会影响运行时
- ⚠️ **Token 权限最小化**：只授予 `repo` 权限即可
- ⚠️ **定期更新 token**：建议设置提醒，在 token 过期前更新

## 故障排查

### 错误：未设置 GITHUB_TOKEN 环境变量

**原因**：Vercel 环境变量未配置或配置错误

**解决**：
1. 检查 Vercel 项目设置中的环境变量
2. 确认变量名是 `GITHUB_TOKEN`（区分大小写）
3. 确认变量已应用到所有环境

### 错误：fatal: could not read Username

**原因**：Git 认证失败

**解决**：
1. 检查 token 是否有 `repo` 权限
2. 检查 token 是否已过期
3. 重新生成 token 并更新环境变量

### 错误：Repository not found

**原因**：Token 没有访问该仓库的权限

**解决**：
1. 确认 token 的 `repo` 权限已启用
2. 确认 token 是由有仓库访问权限的账号创建的
3. 如果是组织仓库，确认 token 有访问组织仓库的权限

## 替代方案

如果上述方案不生效，可以考虑：

1. **发布到 PyPI**：将 `micro-life-sim` 发布到 PyPI（公开或私有），然后在 `requirements.txt` 中使用 PyPI 版本
2. **使用 GitHub Packages**：将包发布到 GitHub Packages，使用 pip 的 `--extra-index-url` 配置

## 相关文件

- `build.sh` - 构建脚本，配置 Git 认证
- `requirements.txt` - Python 依赖列表
- `vercel.json` - Vercel 配置文件

