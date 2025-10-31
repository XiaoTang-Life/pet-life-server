# 快速开始

## 本地开发运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动本地服务

```bash
fastapi dev main.py
```

或者使用uvicorn：

```bash
uvicorn main:app --reload
```

你应该看到类似的输出：
```
🐾 Pet Life Server 启动中...
📚 API文档: http://localhost:8000/docs
```

### 3. 访问API

- **API文档**: http://localhost:8000/docs (自动生成的Swagger UI)
- **健康检查**: http://localhost:8000/health

### 4. 测试API

运行测试脚本（在另一个终端）：

```bash
python test_api.py
```

## API 端点

### 健康检查
- `GET /` - 服务状态
- `GET /health` - 健康检查

### 宠物API
- `GET /api/pet/status?device_id=xxx` - 获取宠物状态
- `POST /api/pet/feed` - 喂食
- `POST /api/pet/interact` - 互动（feed/greet/play）

### 调试API
- `POST /api/debug/reset?device_id=xxx` - 重置宠物状态

## 部署到Vercel

### 1. 连接GitHub仓库

```bash
# 首先确保代码已提交到GitHub
git add .
git commit -m "Initial server setup"
git push origin main
```

### 2. 部署到Vercel

访问 https://vercel.com 并：
1. 点击 "New Project"
2. 导入 `pet-life-server` 仓库
3. 框架选择 "Python"
4. 点击 "Deploy"

### 3. 验证部署

部署完成后，Vercel会提供一个URL，例如：
```
https://pet-life-server-xxxx.vercel.app
```

验证部署成功：
```bash
curl https://pet-life-server-xxxx.vercel.app/health
```

## 项目结构

```
pet-life-server/
├── api/
│   └── index.py              # Vercel Functions入口
├── src/
│   ├── models.py            # 数据模型
│   └── pet_adapter.py       # 宠物适配器
├── main.py                  # 本地开发入口
├── requirements.txt         # 依赖
├── vercel.json             # Vercel配置
├── test_api.py             # 测试脚本
└── README.md
```

## 常见问题

### 启动时出现导入错误

确保你在项目根目录运行命令：
```bash
cd pet-life-server
fastapi dev main.py
```

### Vercel部署失败

检查 `vercel.json` 配置，确保Python版本正确：
```json
{
  "functions": {
    "api/index.py": {
      "runtime": "python3.11"
    }
  }
}
```

### 需要环境变量

如果需要添加环境变量（如API密钥），在Vercel项目设置中添加：
1. 进入 Project Settings
2. 找到 "Environment Variables"
3. 添加需要的变量

## 下一步

- [ ] 集成真实的 `micro-life-sim` 引擎
- [ ] 添加数据库存储（Vercel KV）
- [ ] 实现用户认证系统
- [ ] 添加更复杂的宠物行为逻辑
