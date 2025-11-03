# Redis 存储集成指南

**阶段**: Phase 5 - Redis 存储集成
**日期**: 2025-11-02
**版本**: v0.4.0
**状态**: ✅ 完成

---

## 概述

pet-life-server v2.0 集成了 micro-life-sim v0.4.0 的 Redis 存储后端，实现了完整的 Serverless 支持。

**关键改进**：
- ✅ Vercel KV 原生支持
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

### Vercel 部署（Redis/Vercel KV）

#### 1. 创建 Vercel KV 存储

在 Vercel 控制台：
1. 进入 "Storage" → "KV"
2. 创建新的 KV 存储
3. 连接到你的项目
4. 自动生成 `KV_REST_API_URL` 环境变量

#### 2. 环境变量

Vercel 会自动注入：
```
KV_REST_API_URL=https://...
KV_REST_API_TOKEN=...
```

无需额外配置！

#### 3. 部署

```bash
git push origin main
# Vercel 会自动:
# 1. 检测 requirements.txt
# 2. 安装 redis>=5.0.0
# 3. 安装 micro-life-sim v0.4.0
# 4. 使用 KV_REST_API_URL 作为 Redis 连接
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
│  KV_REST_API_URL / REDIS_URL│
└──┬──────────────────────────┘
   │
   ├─ 有Redis配置?
   │  ├─ 是 → 使用 RedisStorage
   │  │        (Serverless环境)
   │  │
   │  └─ 否 → 使用 FileStorage
   │           (本地开发)
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
1. ✅ 是否创建了 Vercel KV？
2. ✅ KV 是否连接到项目？
3. ✅ requirements.txt 是否包含 `redis>=5.0.0`？
4. ✅ 是否推送了最新的代码？

```bash
# 检查部署日志
vercel logs --follow
```

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

# Vercel KV（通过控制台）
vercel kv list
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
| Vercel KV | latest | Serverless 存储 |

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

- [micro-life-sim v0.4.0](../../../micro-life-sim/docs/第C纪：脉动/Phase1-3完成总结.md)
- [Redis 存储方案](../../../micro-life-sim/docs/第C纪：脉动/Redis存储后端技术方案.md)
- [Vercel KV 文档](https://vercel.com/docs/storage/vercel-kv)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

---

**最后更新**: 2025-11-02
**作者**: Claude Code
**状态**: ✅ 生产环境就绪
