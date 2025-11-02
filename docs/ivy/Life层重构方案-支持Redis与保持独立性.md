# Life层重构方案：支持Redis与保持独立性

**文档版本**: v1.0
**创建日期**: 2025-11-02
**作者**: Ivy & AI Assistant
**决策状态**: 🟢 待实施
**适用项目**: micro-life-sim + pet-life-server

---

## 📋 目录

- [1. 重构目标与原则](#1-重构目标与原则)
- [2. 当前架构分析](#2-当前架构分析)
- [3. 重构设计方案](#3-重构设计方案)
- [4. 实施计划](#4-实施计划)
- [5. 向后兼容策略](#5-向后兼容策略)
- [6. 测试策略](#6-测试策略)
- [7. 风险评估](#7-风险评估)

---

## 1. 重构目标与原则

### 1.1 重构目标

**核心目标**：让micro-life-sim的Life类能够无缝支持Redis存储，同时保持独立性和文件存储的兼容性。

```
┌─────────────────────────────────────────────────────────────┐
│                   重构目标金字塔                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│              ┌─────────────────────────┐                    │
│              │   P0: Redis支持          │                    │
│              │   完美适配Serverless     │                    │
│              └─────────────────────────┘                    │
│                         ↑                                   │
│          ┌──────────────┴──────────────┐                    │
│          │     P1: 保持独立性           │                    │
│          │  不依赖特定业务逻辑          │                    │
│          └──────────────┬──────────────┘                    │
│                         ↑                                   │
│     ┌───────────────────┴───────────────────┐               │
│     │         P2: 向后兼容                   │               │
│     │     文件存储模式继续可用                │               │
│     └───────────────────────────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**具体目标**：

1. ✅ **支持Redis后端**：Life类可以使用Redis作为存储后端
2. ✅ **延迟写入优化**：支持`auto_flush=False`模式，减少网络开销
3. ✅ **保持独立性**：不与pet-life-server耦合，可独立使用
4. ✅ **向后兼容**：现有文件存储代码无需修改
5. ✅ **清晰接口**：提供简单明了的API，隐藏实现细节

### 1.2 设计原则

#### **原则1：依赖倒置**

```python
# 不好的设计（紧耦合）
class Life:
    def __init__(self):
        self.storage = FileStorage("./data")  # 硬编码

# 好的设计（依赖抽象）
class Life:
    def __init__(self, backend='file', **config):
        if backend == 'file':
            self.storage = FileStorage(config['state_dir'])
        elif backend == 'redis':
            self.storage = RedisStorage(config['redis_url'], ...)
```

#### **原则2：最小知识**

Life类不需要知道：
- Redis的连接细节
- Key前缀的命名规范
- TTL的具体值

Life类只需知道：
- 我需要保存状态
- 我需要加载状态
- 我需要刷新状态到存储

#### **原则3：单一职责**

```
Life (协调器)
  ├─ 职责：管理生命周期、协调子系统
  └─ 不管：具体的存储实现

StateManager (存储管理器)
  ├─ 职责：抽象存储接口、选择后端
  └─ 不管：生命逻辑

StorageBackend (存储后端)
  ├─ 职责：具体的读写实现
  └─ 不管：业务逻辑
```

#### **原则4：开闭原则**

- **对扩展开放**：可以轻松添加新的存储后端（MongoDB、PostgreSQL等）
- **对修改封闭**：添加新后端不需要修改Life类或StateManager的核心逻辑

---

## 2. 当前架构分析

### 2.1 当前Life类结构

```python
class Life:
    """当前实现（v0.3）"""

    def __init__(self, state_dir: str = None, time_scale: float = 1.0):
        # 问题1：只支持文件存储
        self.state_manager = StateManager(state_dir)

        # 问题2：ProcessLock在Serverless环境不可用
        self.process_lock = ProcessLock(state_dir)

        # ✅ 良好设计：子系统组合
        self.rhythm = RhythmSystem()
        self.energy = EnergySystem()

        # ✅ 良好设计：元信息管理
        self.birth_time = datetime.now()
        self.life_id = 1
```

### 2.2 当前StateManager结构

```python
class StateManager:
    """当前实现（v0.3）"""

    def __init__(self, state_dir: str):
        # 问题：硬编码文件存储
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def load(self, system_name: str) -> Dict[str, Any]:
        """从文件加载"""
        file_path = self.state_dir / f"{system_name}.json"
        # ...

    def save(self, system_name: str, state: Dict[str, Any]) -> None:
        """保存到文件"""
        file_path = self.state_dir / f"{system_name}.json"
        # ...
```

### 2.3 pet-life-server当前使用方式

```python
# src/life_adapter.py (当前实现)
class LifeAdapter:
    def __init__(self, device_id: str):
        # 每个设备独立的状态目录
        state_dir = f"/tmp/life-{device_id}"

        # 创建Life实例
        life = Life(state_dir=state_dir)

        # 问题1：文件存储在Vercel的临时文件系统
        # 问题2：冷启动时数据丢失
        # 问题3：无法跨实例共享
```

---

## 3. 重构设计方案

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Life (v0.4)                             │
│                                                             │
│  def __init__(self, backend='file', auto_flush=True,        │
│              state_dir=None, redis_url=None,                │
│              device_id=None, ttl=None, **kwargs):           │
│                                                             │
│      1. 选择存储后端（backend参数）                          │
│      2. 传递配置给StateManager                               │
│      3. 决定是否使用ProcessLock                             │
│      4. 初始化子系统                                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                  新增方法：flush()                           │
│      def flush(self) -> None:                               │
│          """手动刷新状态到存储后端"""                        │
│          self.state_manager.flush()                         │
└─────────────────────────────────────────────────────────────┘
                          ↓ 使用
┌─────────────────────────────────────────────────────────────┐
│               StateManager (v0.4改造)                        │
│                                                             │
│  def __init__(self, backend='file', auto_flush=True,        │
│              **config):                                     │
│                                                             │
│      1. 根据backend选择存储后端                             │
│      2. 初始化_pending_saves缓冲区                          │
│      3. 设置auto_flush模式                                  │
│                                                             │
│  核心机制：                                                  │
│  • save() → 立即写入 or 缓冲到_pending_saves                 │
│  • flush() → 批量提交_pending_saves                         │
│  • load() → 优先返回_pending_saves中的数据                  │
└─────────────────────────────────────────────────────────────┘
                          ↓ 委托
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌──────────────────┐              ┌──────────────────┐
│  FileStorage     │              │  RedisStorage    │
│                  │              │                  │
│  • load()        │              │  • load()        │
│  • save()        │              │  • save()        │
│  • delete()      │              │  • delete()      │
│  • exists()      │              │  • exists()      │
└──────────────────┘              └──────────────────┘
        ↓                                   ↓
┌──────────────────┐              ┌──────────────────┐
│  本地文件系统      │              │  Redis/Vercel KV │
│  *.json          │              │  life:dev:*      │
└──────────────────┘              └──────────────────┘
```

### 3.2 Life类重构API

#### **3.2.1 构造函数设计**

```python
class Life:
    """重构后的Life类（v0.4）"""

    def __init__(
        self,
        # ===== 存储后端配置 =====
        backend: str = 'file',
        state_dir: str = None,
        redis_url: str = None,
        device_id: str = None,
        ttl: int = None,
        auto_flush: bool = True,
        use_process_lock: bool = None,  # None = 自动检测

        # ===== 其他配置 =====
        time_scale: float = 1.0
    ):
        """
        初始化生命体

        Args:
            backend: 存储后端类型
                - 'file': 文件存储（默认，本地开发）
                - 'redis': Redis存储（Server端）

            state_dir: 文件存储目录（backend='file'时必需）
                示例：'./data' 或 '/tmp/life-device-123'

            redis_url: Redis连接字符串（backend='redis'时必需）
                示例：'redis://localhost:6379/0'
                Vercel: os.getenv('KV_URL')

            device_id: 设备ID，用作Redis key前缀（backend='redis'时必需）
                示例：'device-123'

            ttl: Redis key过期时间（秒，backend='redis'时可选）
                示例：2592000（30天）
                默认：None（永不过期）

            auto_flush: 是否自动写入
                - True: 每次tick立即写入（默认，实时模式）
                - False: 延迟写入到内存，需手动flush()

            use_process_lock: 是否使用进程锁
                - True: 使用（本地开发推荐）
                - False: 不使用（Serverless必需）
                - None: 自动检测（Redis后端自动设为False）

            time_scale: 时间加速倍数（测试用）
                示例：1.0（正常），60.0（1分钟=1小时）

        使用示例：

            # 场景1：本地开发（文件存储，默认配置）
            life = Life(state_dir='./data')

            # 场景2：本地开发（Redis测试）
            life = Life(
                backend='redis',
                redis_url='redis://localhost:6379/0',
                device_id='dev-1',
                use_process_lock=True  # 本地可用锁
            )

            # 场景3：Server端（Redis + 延迟写入）✨ 推荐
            life = Life(
                backend='redis',
                redis_url=os.getenv('KV_URL'),
                device_id='device-123',
                ttl=2592000,  # 30天过期
                auto_flush=False,  # 性能优化
                use_process_lock=False  # Serverless不可用锁
            )
        """

        # ===== 1. 配置StateManager =====
        if backend == 'file':
            if not state_dir:
                raise ValueError("state_dir is required for file backend")

            config = {
                'backend': 'file',
                'state_dir': state_dir,
                'auto_flush': auto_flush
            }

            # 自动检测：文件后端默认使用进程锁
            if use_process_lock is None:
                use_process_lock = True

        elif backend == 'redis':
            if not redis_url:
                raise ValueError("redis_url is required for redis backend")
            if not device_id:
                raise ValueError("device_id is required for redis backend")

            config = {
                'backend': 'redis',
                'redis_url': redis_url,
                'key_prefix': f"life:{device_id}",
                'ttl': ttl,
                'auto_flush': auto_flush
            }

            # 自动检测：Redis后端默认不使用进程锁
            if use_process_lock is None:
                use_process_lock = False

        else:
            raise ValueError(f"Unknown backend: {backend}")

        # ===== 2. 初始化StateManager =====
        self.state_manager = StateManager(**config)

        # ===== 3. 初始化ProcessLock（可选）=====
        if use_process_lock and backend == 'file':
            self.process_lock = ProcessLock(state_dir)
        else:
            self.process_lock = None

        # ===== 4. 初始化子系统 =====
        self.rhythm = RhythmSystem()
        self.energy = EnergySystem()

        self.systems: Dict[str, BaseSystem] = {
            "rhythm": self.rhythm,
            "energy": self.energy
        }

        # ===== 5. 运行状态 =====
        self.running = False
        self.start_time = None
        self.time_scale = time_scale
        self.tick_count = 0

        # ===== 6. 元信息 =====
        from datetime import datetime
        self.birth_time = datetime.now()
        self.life_id = 1

        # ===== 7. 从存储恢复状态 =====
        self._load_states()
```

#### **3.2.2 新增flush()方法**

```python
def flush(self) -> None:
    """手动刷新状态到存储后端

    工作机制：
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    当 auto_flush=False 时：
    - tick() 只在内存中更新状态（_pending_saves）
    - 必须调用 flush() 才会真正写入存储

    当 auto_flush=True 时：
    - tick() 每次都立即写入存储
    - flush() 调用无副作用（缓冲区为空）
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    使用示例：
        life = Life(backend='redis', ..., auto_flush=False)
        life.start()

        # 批量tick（全在内存中）
        for _ in range(1440):
            life.tick()

        # 最后一次性写入Redis
        life.flush()  # ← 只需2次网络请求

        life.stop()

    性能收益：
        - auto_flush=True: 1440次tick = 2880次Redis请求 (~2.88秒)
        - auto_flush=False: 1440次tick + flush = 2次Redis请求 (~12ms)
        - 性能提升：240倍！
    """
    self.state_manager.flush()
```

#### **3.2.3 start()方法改进**

```python
def start(self) -> bool:
    """启动生命体

    返回值：
        True: 启动成功
        False: 进程锁被占用（仅当use_process_lock=True时）

    改进点：
    - 兼容无锁模式（Serverless环境）
    - 保持原有API不变
    """
    # 如果使用进程锁
    if self.process_lock:
        if not self.process_lock.acquire():
            return False  # 锁被占用

    # 设置运行状态
    self.running = True
    self.start_time = time.time()
    self.tick_count = 0

    return True
```

#### **3.2.4 stop()方法改进**

```python
def stop(self) -> None:
    """停止生命体

    改进点：
    - 确保调用flush()，防止数据丢失
    - 兼容无锁模式
    """
    if not self.running:
        return

    self.running = False

    # ← 关键：确保所有待写入的状态都被刷新
    self.flush()

    # 释放进程锁（如果有）
    if self.process_lock:
        self.process_lock.release()
```

### 3.3 pet-life-server集成方式

#### **3.3.1 LifeAdapter重构**

```python
# src/life_adapter.py（重构后）

import os
from life import Life
from typing import Dict

class LifeAdapter:
    """为pet-life-server适配Life引擎（v0.4）"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.redis_url = os.getenv('KV_URL')

        if not self.redis_url:
            raise ValueError("KV_URL environment variable not set")

    def create_life(self) -> Life:
        """创建Life实例（Redis后端，延迟写入）"""
        return Life(
            backend='redis',
            redis_url=self.redis_url,
            device_id=self.device_id,
            ttl=2592000,  # 30天过期
            auto_flush=False,  # ✨ 性能优化：延迟写入
            use_process_lock=False  # Serverless环境不使用锁
        )

    def get_state(self) -> Dict:
        """获取当前宠物状态"""
        life = self.create_life()

        # 启动（从Redis加载状态）
        if not life.start():
            raise RuntimeError("Failed to start life instance")

        try:
            # 计算时间差并推进
            minutes_elapsed = self._calculate_elapsed_minutes(life)

            # 批量tick（全在内存中）
            for _ in range(minutes_elapsed):
                life.tick()

            # 一次性写入Redis
            life.flush()

            # 获取最终状态
            states = life.get_states()
            expression = life.get_expression()

            return {
                'internal_state': states,
                'expression': expression,
                'device_id': self.device_id,
                'minutes_elapsed': minutes_elapsed
            }

        finally:
            # 确保资源释放
            life.stop()

    def _calculate_elapsed_minutes(self, life: Life) -> int:
        """计算距离上次更新的分钟数"""
        # 从Redis加载的状态中获取last_update
        states = life.get_states()

        if 'rhythm' in states and 'last_update' in states['rhythm']:
            from datetime import datetime
            last_update = states['rhythm']['last_update']
            now = datetime.now().timestamp()
            minutes = int((now - last_update) / 60)
            return max(0, min(minutes, 10080))  # 上限7天

        return 0

    def interact(self, action: str) -> Dict:
        """处理用户交互"""
        life = self.create_life()
        life.start()

        try:
            # 先推进时间
            minutes_elapsed = self._calculate_elapsed_minutes(life)
            for _ in range(minutes_elapsed):
                life.tick()

            # 执行交互
            if action == 'feed':
                self._apply_feed(life)
            elif action == 'play':
                self._apply_play(life)
            elif action == 'greet':
                self._apply_greet(life)

            # 一次tick反映交互效果
            life.tick()

            # 刷新到Redis
            life.flush()

            return {
                'internal_state': life.get_states(),
                'expression': life.get_expression(),
                'action': action
            }

        finally:
            life.stop()

    def _apply_feed(self, life: Life):
        """应用喂食效果"""
        energy_state = life.state_manager.load("energy")
        energy_state["energy"] = min(100, energy_state["energy"] + 20)
        life.state_manager.save("energy", energy_state)

    def _apply_play(self, life: Life):
        """应用玩耍效果"""
        energy_state = life.state_manager.load("energy")
        energy_state["energy"] = max(0, energy_state["energy"] - 10)
        life.state_manager.save("energy", energy_state)

    def _apply_greet(self, life: Life):
        """应用打招呼效果"""
        # 可以添加心情系统后实现
        pass
```

#### **3.3.2 API端点更新**

```python
# main.py 或 api/index.py（无需修改！）

@app.get("/api/pet/status")
async def get_pet_status(device_id: str):
    """获取宠物状态（自动推进时间）"""
    try:
        adapter = LifeAdapter(device_id)
        state = adapter.get_state()

        return {
            "success": True,
            "data": state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pet/interact")
async def interact_pet(request: InteractRequest):
    """宠物互动"""
    try:
        adapter = LifeAdapter(request.device_id)
        state = adapter.interact(request.action)

        return {
            "success": True,
            "data": state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 4. 实施计划

### 4.1 实施步骤

#### **Phase 1：基础设施（1-2天）**

```
任务1.1: 创建StorageBackend抽象接口
  文件：src/core/storage_backend.py
  内容：定义load/save/delete/exists抽象方法

任务1.2: 实现FileStorage
  文件：src/core/file_storage.py
  内容：重构当前StateManager的文件存储逻辑

任务1.3: 实现RedisStorage
  文件：src/core/redis_storage.py
  内容：参考文档"Redis存储后端技术方案.md"

任务1.4: 改造StateManager
  文件：src/core/state_manager.py
  修改：
    - 添加backend参数
    - 添加auto_flush参数
    - 实现_pending_saves缓冲机制
    - 实现flush()方法
```

**验收标准**：
```python
# 测试FileStorage（保持向后兼容）
sm = StateManager(backend='file', state_dir='./data')
sm.save("test", {"value": 123})
assert sm.load("test")["value"] == 123

# 测试RedisStorage
sm = StateManager(
    backend='redis',
    redis_url='redis://localhost:6379/0',
    key_prefix='test'
)
sm.save("test", {"value": 456})
assert sm.load("test")["value"] == 456

# 测试延迟写入
sm = StateManager(backend='file', state_dir='./data', auto_flush=False)
sm.save("test", {"value": 789})
assert sm.load("test")["value"] == 789  # 从_pending_saves读取
sm.flush()  # 刷新到文件
```

#### **Phase 2：Life类重构（1天）**

```
任务2.1: 修改Life.__init__()
  文件：src/life.py
  修改：
    - 添加backend参数
    - 添加redis_url、device_id、ttl参数
    - 添加auto_flush参数
    - 添加use_process_lock参数
    - 实现后端选择逻辑

任务2.2: 添加Life.flush()方法
  文件：src/life.py
  内容：简单代理给self.state_manager.flush()

任务2.3: 改进Life.start()
  文件：src/life.py
  修改：兼容无锁模式

任务2.4: 改进Life.stop()
  文件：src/life.py
  修改：确保调用flush()
```

**验收标准**：
```python
# 测试文件后端（向后兼容）
life = Life(state_dir='./data')
life.start()
life.tick()
life.stop()

# 测试Redis后端
life = Life(
    backend='redis',
    redis_url='redis://localhost:6379/0',
    device_id='test-1'
)
life.start()
life.tick()
life.stop()

# 测试延迟写入
life = Life(
    backend='redis',
    redis_url='redis://localhost:6379/0',
    device_id='test-2',
    auto_flush=False
)
life.start()
for _ in range(10):
    life.tick()
life.flush()
life.stop()
```

#### **Phase 3：pet-life-server集成（0.5天）**

```
任务3.1: 重构LifeAdapter
  文件：pet-life-server/src/life_adapter.py
  修改：
    - 使用新的Life API
    - 设置backend='redis'
    - 设置auto_flush=False
    - 设置use_process_lock=False

任务3.2: 更新requirements.txt
  文件：pet-life-server/requirements.txt
  修改：更新micro-life-sim版本引用
```

**验收标准**：
```bash
# 本地测试
cd pet-life-server
python -m pytest tests/

# Vercel部署测试
vercel --prod
curl https://your-app.vercel.app/api/pet/status?device_id=test-1
```

#### **Phase 4：测试和文档（1天）**

```
任务4.1: 单元测试
  文件：
    - tests/test_file_storage.py
    - tests/test_redis_storage.py
    - tests/test_state_manager.py
    - tests/test_life_redis.py

任务4.2: 集成测试
  文件：tests/test_integration_redis.py
  内容：测试完整的Life → Redis → Life流程

任务4.3: 性能测试
  文件：benchmarks/bench_redis.py
  内容：对比auto_flush=True/False的性能

任务4.4: 文档更新
  文件：
    - README.md（添加Redis使用示例）
    - CHANGELOG.md（记录v0.4变更）
    - docs/Redis-Integration-Guide.md（集成指南）
```

### 4.2 时间线

```
第1天：Phase 1 - 基础设施
  ├─ 上午：StorageBackend接口 + FileStorage
  └─ 下午：RedisStorage + StateManager改造

第2天：Phase 2 - Life类重构
  ├─ 上午：Life.__init__()改造 + flush()
  └─ 下午：start()/stop()改进 + 本地测试

第3天：Phase 3 + Phase 4 - 集成和测试
  ├─ 上午：LifeAdapter重构 + API测试
  └─ 下午：单元测试 + 文档更新

总计：3天（实际可能2-4天，取决于测试覆盖度）
```

---

## 5. 向后兼容策略

### 5.1 API兼容性

#### **保持向后兼容的API**

```python
# ✅ v0.3代码无需修改，仍然可用
life = Life(state_dir='./data')
life.start()
life.tick()
life.stop()

# ✅ v0.4新增API（可选使用）
life = Life(
    backend='redis',
    redis_url='...',
    device_id='...'
)
```

#### **默认行为保持不变**

```python
# v0.3默认行为
Life(state_dir='./data')
# ↓ 等价于 ↓
# v0.4默认行为
Life(
    backend='file',          # 默认文件存储
    state_dir='./data',
    auto_flush=True,         # 默认实时写入
    use_process_lock=True    # 默认使用锁（文件后端）
)
```

### 5.2 弃用策略

**不删除任何现有API**，只标记为"推荐使用新方式"：

```python
class Life:
    def __init__(self, state_dir: str = None, time_scale: float = 1.0, **kwargs):
        """初始化生命体

        Args:
            state_dir: (已过时，但仍支持) 状态目录
                推荐使用: backend='file', state_dir='...'

            time_scale: 时间加速倍数

            **kwargs: 新增参数
                - backend: 'file' | 'redis'
                - redis_url: Redis连接字符串
                - device_id: 设备ID
                - ttl: Redis TTL
                - auto_flush: 延迟写入开关
                - use_process_lock: 进程锁开关
        """

        # ✅ 向后兼容：state_dir参数仍然有效
        if state_dir and 'backend' not in kwargs:
            kwargs['backend'] = 'file'
            kwargs['state_dir'] = state_dir

        # 调用新的初始化逻辑
        self._init_v04(**kwargs)
```

### 5.3 迁移指南

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# v0.3代码（继续可用）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from life import Life

life = Life(state_dir='./data')
life.start()
life.tick()
life.stop()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# v0.4迁移到Redis（推荐）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from life import Life
import os

life = Life(
    backend='redis',
    redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    device_id='my-device',
    ttl=2592000,  # 30天
    auto_flush=False  # 性能优化
)
life.start()

# 批量tick
for _ in range(1440):
    life.tick()

# 刷新到Redis
life.flush()

life.stop()
```

---

## 6. 测试策略

### 6.1 单元测试

#### **test_file_storage.py**

```python
import pytest
from core.file_storage import FileStorage

def test_save_and_load():
    storage = FileStorage('/tmp/test-storage')
    storage.save('test', {'value': 123})
    assert storage.load('test')['value'] == 123

def test_delete():
    storage = FileStorage('/tmp/test-storage')
    storage.save('test', {'value': 456})
    assert storage.exists('test')
    storage.delete('test')
    assert not storage.exists('test')

def test_atomic_write():
    """测试原子性写入"""
    storage = FileStorage('/tmp/test-storage')

    # 模拟并发写入
    import threading
    errors = []

    def writer(value):
        try:
            storage.save('concurrent', {'value': value})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 验证：不应该有错误
    assert len(errors) == 0

    # 验证：文件应该存在且可读
    data = storage.load('concurrent')
    assert 'value' in data
```

#### **test_redis_storage.py**

```python
import pytest
from core.redis_storage import RedisStorage

@pytest.fixture
def redis_storage():
    storage = RedisStorage(
        redis_url='redis://localhost:6379/15',  # 测试数据库
        key_prefix='test',
        ttl=60
    )
    yield storage
    # 清理
    storage.delete_all()

def test_save_and_load(redis_storage):
    redis_storage.save('rhythm', {'value': 123})
    assert redis_storage.load('rhythm')['value'] == 123

def test_ttl(redis_storage):
    import time
    storage = RedisStorage(
        redis_url='redis://localhost:6379/15',
        key_prefix='test_ttl',
        ttl=2  # 2秒过期
    )

    storage.save('rhythm', {'value': 789})
    assert storage.exists('rhythm')

    time.sleep(3)
    assert not storage.exists('rhythm')

    storage.delete_all()

def test_key_prefix(redis_storage):
    """测试key前缀隔离"""
    storage1 = RedisStorage('redis://localhost:6379/15', 'device1')
    storage2 = RedisStorage('redis://localhost:6379/15', 'device2')

    storage1.save('rhythm', {'device': 1})
    storage2.save('rhythm', {'device': 2})

    assert storage1.load('rhythm')['device'] == 1
    assert storage2.load('rhythm')['device'] == 2

    storage1.delete_all()
    storage2.delete_all()
```

#### **test_state_manager.py**

```python
def test_auto_flush_true():
    """测试实时写入模式"""
    sm = StateManager(backend='file', state_dir='/tmp/test', auto_flush=True)

    sm.save('rhythm', {'value': 123})

    # 立即从文件加载应该能读到
    import json
    from pathlib import Path
    file_path = Path('/tmp/test/rhythm.json')
    data = json.load(open(file_path))
    assert data['value'] == 123

def test_auto_flush_false():
    """测试延迟写入模式"""
    sm = StateManager(backend='file', state_dir='/tmp/test', auto_flush=False)

    sm.save('rhythm', {'value': 456})

    # 从_pending_saves加载应该能读到
    assert sm.load('rhythm')['value'] == 456

    # 但文件还不存在
    from pathlib import Path
    file_path = Path('/tmp/test/rhythm.json')
    assert not file_path.exists()

    # 调用flush后文件才存在
    sm.flush()
    assert file_path.exists()
```

### 6.2 集成测试

#### **test_life_redis.py**

```python
def test_life_redis_persistence():
    """测试Redis持久化"""
    # 第一个Life实例
    life1 = Life(
        backend='redis',
        redis_url='redis://localhost:6379/15',
        device_id='test-device',
        ttl=60
    )
    life1.start()
    life1.tick()
    life1.tick()
    energy1 = life1.get_states()['energy']['energy']
    life1.stop()

    # 第二个Life实例应该能加载相同状态
    life2 = Life(
        backend='redis',
        redis_url='redis://localhost:6379/15',
        device_id='test-device',
        ttl=60
    )
    life2.start()
    energy2 = life2.get_states()['energy']['energy']
    life2.stop()

    # 验证：能量应该相同
    assert energy1 == energy2

def test_delayed_flush_performance():
    """测试延迟写入性能"""
    import time

    # 测试auto_flush=True
    life1 = Life(
        backend='redis',
        redis_url='redis://localhost:6379/15',
        device_id='bench-auto',
        auto_flush=True
    )
    life1.start()

    start = time.time()
    for _ in range(100):
        life1.tick()
    elapsed_auto = time.time() - start
    life1.stop()

    # 测试auto_flush=False
    life2 = Life(
        backend='redis',
        redis_url='redis://localhost:6379/15',
        device_id='bench-delayed',
        auto_flush=False
    )
    life2.start()

    start = time.time()
    for _ in range(100):
        life2.tick()
    life2.flush()
    elapsed_delayed = time.time() - start
    life2.stop()

    print(f"auto_flush=True: {elapsed_auto:.3f}s")
    print(f"auto_flush=False: {elapsed_delayed:.3f}s")
    print(f"Speedup: {elapsed_auto / elapsed_delayed:.1f}x")

    # 验证：延迟写入应该更快
    assert elapsed_delayed < elapsed_auto
```

### 6.3 性能基准测试

```python
# benchmarks/bench_redis.py

def benchmark_scenarios():
    """对比不同场景的性能"""

    scenarios = [
        ("File + auto_flush=True", {
            'backend': 'file',
            'state_dir': '/tmp/bench-file-auto',
            'auto_flush': True
        }),
        ("File + auto_flush=False", {
            'backend': 'file',
            'state_dir': '/tmp/bench-file-delayed',
            'auto_flush': False
        }),
        ("Redis + auto_flush=True", {
            'backend': 'redis',
            'redis_url': 'redis://localhost:6379/0',
            'device_id': 'bench-redis-auto',
            'auto_flush': True
        }),
        ("Redis + auto_flush=False", {
            'backend': 'redis',
            'redis_url': 'redis://localhost:6379/0',
            'device_id': 'bench-redis-delayed',
            'auto_flush': False
        })
    ]

    results = []

    for name, config in scenarios:
        life = Life(**config)
        life.start()

        start = time.time()
        for _ in range(1440):  # 24小时
            life.tick()
        if not config.get('auto_flush', True):
            life.flush()
        elapsed = time.time() - start

        life.stop()

        results.append((name, elapsed))
        print(f"{name}: {elapsed:.3f}s")

    return results
```

---

## 7. 风险评估

### 7.1 技术风险

| 风险 | 影响 | 概率 | 缓解方案 | 优先级 |
|------|------|------|----------|--------|
| **Redis连接失败** | 服务不可用 | 中 | 连接重试 + 降级到缓存 | P0 |
| **向后兼容性破坏** | 现有代码无法运行 | 低 | 充分测试 + API兼容设计 | P0 |
| **性能不达预期** | 延迟写入提升不明显 | 低 | 基准测试验证 | P1 |
| **ProcessLock在Serverless失败** | 已知问题 | 高 | use_process_lock=False | P0 |
| **Redis数据丢失** | 状态重置 | 低 | TTL设置合理 + 监控 | P1 |

### 7.2 实施风险

| 风险 | 影响 | 缓解方案 |
|------|------|----------|
| **实施时间超期** | 延迟上线 | 分阶段实施，Phase 1-2独立可测 |
| **测试覆盖不足** | 线上Bug | 强制单元测试覆盖率>80% |
| **文档不完善** | 使用困难 | 同步更新README和示例代码 |

### 7.3 回滚策略

```python
# 如果v0.4出现严重问题，回滚方案：

# 方案1：回退到v0.3
pip install micro-life-sim==0.3.0

# 方案2：使用向后兼容模式
life = Life(state_dir='./data')  # 不使用新功能

# 方案3：临时禁用Redis后端
# 在pet-life-server中硬编码backend='file'
life = Life(backend='file', state_dir=f'/tmp/life-{device_id}')
```

---

## 附录

### A. 关键文件清单

**micro-life-sim项目**：

| 文件 | 状态 | 说明 |
|------|------|------|
| `src/life.py` | 修改 | 添加backend/redis参数，添加flush()方法 |
| `src/core/state_manager.py` | 修改 | 支持多后端，添加auto_flush |
| `src/core/storage_backend.py` | 新增 | 抽象接口 |
| `src/core/file_storage.py` | 新增 | 文件存储实现 |
| `src/core/redis_storage.py` | 新增 | Redis存储实现 |
| `tests/test_file_storage.py` | 新增 | 文件存储测试 |
| `tests/test_redis_storage.py` | 新增 | Redis存储测试 |
| `tests/test_life_redis.py` | 新增 | 集成测试 |
| `README.md` | 修改 | 添加Redis使用示例 |
| `CHANGELOG.md` | 修改 | 记录v0.4变更 |

**pet-life-server项目**：

| 文件 | 状态 | 说明 |
|------|------|------|
| `src/life_adapter.py` | 修改 | 使用新API，设置Redis后端 |
| `requirements.txt` | 修改 | 更新micro-life-sim版本 |

### B. 性能目标

| 指标 | 目标 | 当前(v0.3) | 预期(v0.4) |
|------|------|-----------|-----------|
| 1440次tick耗时（Redis） | <50ms | N/A | ~12ms |
| 100并发请求吞吐量 | >1000 req/min | N/A | ~5000 req/min |
| 内存占用（单实例） | <5MB | ~3MB | ~2MB |
| Redis请求数（1440次tick） | <10 | N/A | 2 |

### C. 修订历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2025-11-02 | Ivy & AI | 初始版本，Life层重构方案 |

---

**文档结束**
