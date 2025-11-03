# Redis 存储集成指南

**阶段**: Phase 5 - Redis 存储集成
**日期**: 2025-11-02 (更新: 2025-11-03)
**版本**: v0.4.0
**状态**: ✅ 完成
**更新**: Vercel Marketplace 集成指南

> **重要**: 自 2025 年 6 月 9 日起，Vercel 官方 KV 服务已被 Vercel Marketplace 的存储集成所替代。本指南已更新为使用 Upstash（通过 Vercel Marketplace）的新方法。

---

## 概述

pet-life-server v2.0 集成了 micro-life-sim v0.4.0 的 Redis 存储后端，实现了完整的 Serverless 支持。

**关键改进**：
- ✅ Vercel Marketplace 集成（Upstash）
- ✅ 延迟刷盘性能优化（132倍）
- ✅ 自动降级到文件存储（本地开发）
- ✅ 按设备隔离的 Redis 键空间

---

## 环境配置

### 本地开发（文件存储）

无需配置，自动使用文件存储：

```bash
cd pet-life-server
pip install -r requirements.txt
python main.py
```

### Vercel 部署（Vercel Marketplace - Upstash）

> **背景**: Vercel KV 服务已在 2025-06-09 被 Vercel Marketplace 集成所替代。现在需要通过 Marketplace 使用第三方 Redis 提供商，推荐使用 Upstash。

#### 1. 通过 Vercel Marketplace 添加 Upstash

在 Vercel 控制台：
1. 进入项目 → "Storage" 或 "Integrations"
2. 在 Marketplace 中搜索 "Upstash"
3. 点击 "Add" 或 "Connect"
4. 选择免费层或付费计划
5. 授权并连接到项目
6. 自动生成 Redis 连接环境变量

#### 2. 环境变量

Vercel 会自动注入 Upstash 的环境变量：
```
REDIS_URL=redis://default:[password]@[host]:[port]
# 或其他 Upstash 提供的环境变量名称
```

如果环境变量名称不同，可在 Vercel 项目设置中重命名或查看正确的变量名。

#### 3. 部署

```bash
git push origin main
# Vercel 会自动:
# 1. 检测 requirements.txt
# 2. 安装 redis>=5.0.0
# 3. 安装 micro-life-sim v0.4.0
# 4. 使用 REDIS_URL 作为 Redis 连接
# 5. 自动连接到 Upstash Redis 实例
```

#### 4. 验证部署

部署完成后，检查日志确保 Redis 连接成功：
```bash
vercel logs --follow
# 应该看到: "Using RedisStorage with Upstash"
# 或类似的成功连接信息
```

---

## 架构设计

### 存储后端选择流程

```
┌─────────────────────────────┐
│  LifeAdapter 初始化          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  检查环境变量                 │
│  (Marketplace 集成/本地配置) │
│  REDIS_URL / 其他环境变量     │
└──┬──────────────────────────┘
   │
   ├─ 有 Redis 配置?
   │  ├─ 是 → 使用 RedisStorage
   │  │        ├─ Vercel Marketplace (Upstash)
   │  │        ├─ 本地 Redis 实例
   │  │        └─ 其他 Redis 兼容服务
   │  │
   │  └─ 否 → 使用 FileStorage
   │           (本地开发环境)
   │
   └─ 无论哪种，都通过
      统一的 Storage API
```

### 键空间隔离

每个设备有独立的 Redis 键：

```
life_device_id_1:rhythm
life_device_id_1:energy

life_device_id_2:rhythm
life_device_id_2:energy
```

这样保证多个用户不会互相干扰。

### 延迟刷盘优化

```python
# LifeAdapter 初始化时：
life = Life(
    backend=redis_backend,
    auto_flush=False  # 关键！
)

# tick 操作：
life.tick(dt=1.0)  # 仅写缓存（极快）

# API 响应时刷盘：
life.flush()  # 一次性写入到 Redis
```

**性能对比**：
- 自动刷盘：1440 tick = 0.639秒（等同2880次Redis写）
- 延迟刷盘：1440 tick = 0.005秒（仅2次Redis写）

---

## API 集成

### 现有 API

#### GET `/api/pet/{device_id}/state`
获取宠物状态（自动读取Redis）

```json
{
  "device_id": "device_123",
  "pet_name": "小糖",
  "internal_state": {
    "rhythm": { "internal_phase": 0.5, ... },
    "energy": { "energy": 75.5, ... }
  },
  "expression": {
    "pulse_rate": 92,
    "feeling": "傍晚渐近，但仍有充足的能量",
    ...
  }
}
```

#### POST `/api/pet/{device_id}/interact`
用户互动（自动刷盘）

```json
{
  "action": "feed"  // or "play", "greet"
}
```

### 新增 API：快速补偿

#### POST `/api/pet/{device_id}/catchup`
离线补偿（利用延迟刷盘的132倍性能）

```bash
# 离线24小时后，快速补偿
curl -X POST http://localhost:8000/api/pet/device_123/catchup \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'
```

**性能**：24小时补偿（1440个tick）耗时 <100ms！

---

## 代码示例

### 基本使用

```python
from src.life_adapter import LifeAdapter

# 创建适配器（自动选择 Redis/FileStorage）
adapter = LifeAdapter("device_123")

# 获取状态
state = adapter.get_state()

# 用户互动
state = adapter.interact("play")

# 快速补偿
state = adapter.catchup(hours=24)

# 重置
state = adapter.reset()
```

### FastAPI 集成

```python
from fastapi import FastAPI
from src.life_adapter import LifeAdapter

app = FastAPI()

@app.get("/pet/{device_id}/state")
async def get_state(device_id: str):
    adapter = LifeAdapter(device_id)
    return adapter.get_state()

@app.post("/pet/{device_id}/interact")
async def interact(device_id: str, action: str):
    adapter = LifeAdapter(device_id)
    return adapter.interact(action)

@app.post("/pet/{device_id}/catchup")
async def catchup(device_id: str, hours: int = 24):
    adapter = LifeAdapter(device_id)
    return adapter.catchup(hours)
```

---

## 故障排查

### 问题：本地运行时找不到 redis

**解决方案**：使用 FileStorage（自动降级）

```bash
# 即使没有 Redis，本地仍能正常运行
python main.py
# 会看到日志：Using FileStorage（如果没有设置REDIS_URL）
```

### 问题：Vercel 部署失败

**检查清单**：
1. ✅ 是否通过 Vercel Marketplace 添加了 Upstash？
2. ✅ Upstash 是否连接到项目？
3. ✅ 环境变量是否正确注入（REDIS_URL 或自定义变量）？
4. ✅ requirements.txt 是否包含 `redis>=5.0.0`？
5. ✅ 是否推送了最新的代码？

```bash
# 检查部署日志
vercel logs --follow

# 查看项目环境变量
vercel env list

# 检查 Upstash 连接是否成功
vercel env pull .env.local
# 查看 .env.local 中的 REDIS_URL
```

**常见问题**：
- 如果看到 "Redis connection failed"，检查 Upstash 实例是否在线
- 如果环境变量名不是 REDIS_URL，需要在 main.py 中修改变量名
- 确保没有 IP 白名单限制（Upstash 面向公网时可能需要配置）

### 问题：性能低于预期

检查是否正确使用延迟刷盘：

```python
# ❌ 错误（每次tick都写）
life = Life(backend=redis, auto_flush=True)
for i in range(1440):
    life.tick()  # 1440次Redis写！

# ✅ 正确（仅最后刷盘）
life = Life(backend=redis, auto_flush=False)
for i in range(1440):
    life.tick()  # 仅内存操作
life.flush()  # 1次Redis写
```

---

## 监控和调试

### 检查 Redis 键

```bash
# 本地 Redis
redis-cli keys "life_*"

# Upstash (通过 Web 控制台)
# 1. 访问 console.upstash.com
# 2. 选择你的 Redis 实例
# 3. 使用 Data Browser 查看键
# 4. 或使用 CLI 选项执行命令：keys life_*

# 或使用 Upstash CLI (如果已安装)
upstash redis list-keys --prefix "life_"
```

### 性能指标

在 LifeAdapter 中添加日志：

```python
import time

def interact(self, action: str):
    start = time.time()
    life = self.get_life()
    life.tick(dt=1.0)
    if not life.state_manager.auto_flush:
        life.flush()
    elapsed = time.time() - start
    print(f"interact({action}) took {elapsed*1000:.1f}ms")
    return self.get_state()
```

### 缓存状态

检查延迟刷盘的缓存：

```python
life = adapter.get_life()
dirty_count = len(life.state_manager.dirty_cache)
print(f"Unsaved changes: {dirty_count} systems")
```

---

## 版本信息

| 组件 | 版本 | 说明 |
|------|------|------|
| pet-life-server | 2.0 | Redis 集成版本 |
| micro-life-sim | 0.4.0 | 多存储后端支持 |
| FastAPI | 0.104.1 | Web 框架 |
| redis | 5.0.0+ | Redis 客户端 |
| Vercel Marketplace | latest | Upstash Redis 集成 |
| Upstash | 任意 | Redis 存储服务商 |

---

## 下一步

### 功能完善
- [ ] 实现用户交互影响宠物状态
- [ ] 添加多宠物支持（一个用户多个宠物）
- [ ] 实现宠物社交功能

### 性能优化
- [ ] 缓存状态快照（减少Redis读）
- [ ] 批量API（同时更新多个宠物）
- [ ] WebSocket 实时推送

### 部署优化
- [ ] Docker 镜像
- [ ] CI/CD 自动化
- [ ] 性能基准测试

---

## 参考资源

### 项目文档
- [micro-life-sim v0.4.0](../../../micro-life-sim/docs/第C纪：脉动/Phase1-3完成总结.md)
- [Redis 存储方案](../../../micro-life-sim/docs/第C纪：脉动/Redis存储后端技术方案.md)

### 官方文档
- [Vercel Marketplace 文档](https://vercel.com/marketplace)
- [Upstash Redis 文档](https://upstash.com/docs)
- [Upstash 与 Vercel 集成指南](https://upstash.com/docs/redis/features/integrations/vercel)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

### 迁移指南
- [从 Vercel KV 到 Vercel Marketplace 迁移](https://vercel.com/docs/storage)（需要查阅最新官方文档）

---

**最后更新**: 2025-11-03
**作者**: Claude Code
**状态**: ✅ 生产环境就绪（已更新 Marketplace 集成）
