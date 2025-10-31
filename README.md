Cloud service for xiaotang-life desktop pet | 云端宠物服务

# Pet Life Server

桌面宠物（小糖生命）的云端服务。基于 [micro-life-sim](https://github.com/xiaotang-life/micro-life-sim) 生命引擎，为iOS客户端提供实时宠物状态API和数据同步服务。

## 概述

- **阶段**：Phase 1 - 云端无用户版本
- **技术栈**：Python + FastAPI + Vercel
- **存储**：Vercel KV (Redis)
- **目标**：2-3周内完成基础版本

## 核心功能

- 🐾 宠物状态管理（能量、饥饿、心情）
- 🔄 云端数据同步（设备ID区分）
- 📱 API服务 for iOS Widget & App
- 🌐 跨设备状态恢复
- ⏱️ 分钟级时间推进引擎

## API端点（规划中）

POST /api/pet/status 获取宠物状态 POST /api/pet/interact 宠物互动 POST /api/pet/feed 喂食 POST /api/pet/sync 跨设备同步

## 依赖

- `micro-life-sim` - 生命演化核心引擎
- `fastapi` - Web框架
- `vercel-kv` - Redis存储

## 开发

```bash
# 安装依赖
pip install -r requirements.txt
```

# 本地运行
fastapi dev main.py

# 部署到Vercel
vercel deploy
相关项目
micro-life-sim - 生命引擎
pet-widget-ios - iOS客户端
许可证
MIT
