# micro-life-sim Redis存储后端技术方案

**文档版本**: v1.0
**创建日期**: 2025-10-31
**最后更新**: 2025-11-02
**作者**: Ivy & AI Assistant
**决策状态**: 🟡 待评审
**适用项目**: XiaoTang-Life pet-life-server

---

## 📋 目录

- [1. 背景与动机](#1-背景与动机)
- [2. 问题分析](#2-问题分析)
- [3. 方案设计](#3-方案设计)
- [4. 技术实现](#4-技术实现)
- [5. 性能分析](#5-性能分析)
- [6. 与pet-life-server集成](#6-与pet-life-server集成)
- [7. 部署指南](#7-部署指南)
- [8. 风险评估](#8-风险评估)
- [9. 待决策事项](#9-待决策事项)

---

## 1. 背景与动机

### 1.1 业务场景

**pet-life-server**（桌面宠物云端服务）需要：
- 在Vercel Serverless环境部署
- 为每个设备（device_id）维护独立的生命体实例
- 支持多设备并发访问
- 处理离线时间补算（可能推进数百甚至上千分钟）

### 1.2 当前限制

**micro-life-sim现有存储方案**：
- 使用本地文件系统（`rhythm.json`、`energy.json`）
- 通过`StateManager`管理状态持久化
- 每次`tick()`更新后写入文件

**Serverless环境的冲突**：
- ❌ Vercel的文件系统是**临时的**（每次冷启动重置）
- ❌ 无法依赖本地文件进行状态持久化
- ❌ 高频文件I/O在Serverless环境性能极差

### 1.3 设计目标

为micro-life-sim新增**Redis存储后端**，满足：

1. ✅ **通用性**：保持micro-life-sim的独立性，不绑定特定业务
2. ✅ **兼容性**：不破坏现有的文件存储逻辑
3. ✅ **可扩展性**：支持未来新增其他存储后端（如Postgres、MongoDB）
4. ✅ **性能优化**：支持延迟写入，减少网络开销
5. ✅ **多租户隔离**：通过key前缀区分不同设备/用户

---

## 2. 问题分析

### 2.1 核心问题：高频写入开销

#### **场景**：用户离线24小时后重新上线

```
用户请求 → Server推进1440分钟（24小时）
         → Life.tick() × 1440次
         → StateManager.save() × 2880次（rhythm + energy）
```

#### **文件系统模式的性能瓶颈**

| 操作 | 单次耗时 | 1440次tick总耗时 |
|------|---------|----------------|
| 创建临时文件 | ~3ms | ~4.3秒 |
| 写入数据 | ~2ms | ~2.9秒 |
| fsync刷盘 | ~3ms | ~4.3秒 |
| 原子重命名 | ~2ms | ~2.9秒 |
| **总计** | **~10ms** | **~14.4秒** |

**100个并发请求**：
- 总耗时：14.4秒 × 100 = **1440秒（24分钟）**
- 磁盘写入：288,000次
- /tmp空间占用：可能超出512MB限制

❌ **完全不可接受**

---

#### **Redis模式的性能优势**

| 操作 | 单次耗时 | 1440次tick总耗时 |
|------|---------|----------------|
| Redis SET命令 | ~1ms | ~1.4秒 |

**100个并发请求**：
- 总耗时：1.4秒 × 100 = **140秒（2.3分钟）**
- 提升：**10倍**

✅ **勉强可接受，但仍需优化**

---

#### **Redis + 延迟写入的终极方案**

```python
# 1440次tick在内存中完成
for _ in range(1440):
    life.tick()  # 不写Redis

# 最后一次性写入
life.flush()  # 1次Redis写入
```

| 操作 | 耗时 |
|------|-----|
| 1440次tick（纯内存） | ~10ms |
| 1次Redis写入 | ~1ms |
| **总计** | **~11ms** |

**100个并发请求**：
- 总耗时：11ms × 100 = **1.1秒**
- 提升：**1300倍**

✅ **完美！**

---

### 2.2 设计约束

#### **必须满足**
1. 不破坏micro-life-sim的独立性
2. 支持本地开发（仍用文件系统）
3. Redis作为可选依赖（不强制安装）
4. 支持多种Redis实例（Vercel KV、自建Redis等）

#### **应该满足**
1. 支持延迟写入（性能优化）
2. 支持key前缀（多租户隔离）
3. 支持TTL设置（自动清理过期数据）
4. 易于测试和调试

#### **可以妥协**
1. 不支持Redis集群（MVP阶段单实例即可）
2. 不支持Redis事务（状态更新不需要事务性）
3. 不支持Redis分片（预计用户量不会太大）

---

## 3. 方案设计

### 3.1 架构图

```
┌─────────────────────────────────────────────┐
│           Life (生命体主类)                   │
│                                             │
│  - __init__(backend='file'|'redis', ...)   │
│  - tick()                                   │
│  - flush()  ← 新增：手动刷新状态             │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│         StateManager (状态管理器)            │
│                                             │
│  - __init__(backend, **config)             │
│  - load(system_name)                        │
│  - save(system_name, state)                 │
└──────────────────┬──────────────────────────┘
                   ↓
         ┌─────────┴─────────┐
         ↓                   ↓
┌──────────────────┐  ┌──────────────────┐
│  FileStorage     │  │  RedisStorage    │
│                  │  │                  │
│  - load()        │  │  - load()        │
│  - save()        │  │  - save()        │
│  - delete()      │  │  - delete()      │
└──────────────────┘  └──────────────────┘
         ↓                   ↓
┌──────────────────┐  ┌──────────────────┐
│  本地文件系统      │  │  Redis          │
│  rhythm.json     │  │  life:dev1:rhythm│
│  energy.json     │  │  life:dev1:energy│
└──────────────────┘  └──────────────────┘
```

---

### 3.2 核心接口设计

#### **StorageBackend（抽象基类）**

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class StorageBackend(ABC):
    """存储后端抽象接口"""

    @abstractmethod
    def load(self, key: str) -> Dict[str, Any]:
        """
        加载状态

        Args:
            key: 状态键名（如 "rhythm", "energy"）

        Returns:
            Dict: 状态数据，不存在则返回空字典
        """
        pass

    @abstractmethod
    def save(self, key: str, state: Dict[str, Any]) -> None:
        """
        保存状态

        Args:
            key: 状态键名
            state: 状态数据
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        删除状态

        Args:
            key: 状态键名
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        检查状态是否存在

        Args:
            key: 状态键名

        Returns:
            bool: 存在返回True
        """
        pass
```

---

### 3.3 Redis Key设计

#### **格式**

```
{prefix}:{device_id}:{system_name}
```

#### **示例**

```
life:device-123:rhythm
life:device-123:energy
life:device-456:rhythm
life:device-456:energy
```

#### **说明**
- `prefix`: 统一前缀��默认`"life"`），用于命名空间隔离
- `device_id`: 设备ID，由调用方传入
- `system_name`: 系统名称（`rhythm`、`energy`等）

#### **优势**
- ✅ 多设备隔离（不同device_id互不影响）
- ✅ 易于调试（Redis CLI直接查看）
- ✅ 支持批量操作（SCAN扫描某个device的所有key）
- ✅ 支持通配符删除（如清理某个设备的所有数据）

---

## 4. 技术实现

### 4.1 目录结构

```
micro-life-sim/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state_manager.py      # 改造：支持多后端
│   │   ├── storage_backend.py    # 新增：抽象接口
│   │   ├── file_storage.py       # 新增：文件存储实现
│   │   └── redis_storage.py      # 新增：Redis存储实现
│   ├── life.py                   # 改造：支持backend参数
│   └── ...
├── tests/
│   ├── test_file_storage.py     # 新增
│   ├── test_redis_storage.py    # 新增
│   └── ...
└── pyproject.toml                # 修改：添加可选依赖
```

---

### 4.2 核心代码实现

#### **storage_backend.py（抽象接口）**

```python
#!/usr/bin/env python3
"""
Storage Backend - 存储后端抽象接口

为StateManager提供统一的存储接口，支持多种后端实现
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class StorageBackend(ABC):
    """存储后端抽象基类

    所有存储后端必须实现此接口
    """

    @abstractmethod
    def load(self, key: str) -> Dict[str, Any]:
        """加载状态

        Args:
            key: 状态键名

        Returns:
            Dict: 状态数据，不存在则返回空字典
        """
        pass

    @abstractmethod
    def save(self, key: str, state: Dict[str, Any]) -> None:
        """保存状态

        Args:
            key: 状态键名
            state: 状态数据
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除状态

        Args:
            key: 状态键名
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查状态是否存在

        Args:
            key: 状态键名

        Returns:
            bool: 存在返回True
        """
        pass
```

---

#### **redis_storage.py（Redis存储）**

```python
#!/usr/bin/env python3
"""
Redis Storage - Redis存储后端

用于Serverless环境或需要共享状态的场景
"""

import json
from typing import Dict, Any, Optional

from .storage_backend import StorageBackend

# Redis作为可选依赖
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisStorage(StorageBackend):
    """Redis存储后端

    特性：
    - 支持多设备隔离（通过key_prefix）
    - 支持TTL自动过期
    - 高性能读写
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "life",
        ttl: Optional[int] = None
    ):
        """
        Args:
            redis_url: Redis连接字符串
                格式：redis://[[username]:[password]]@host:port/db
                示例：redis://:password@localhost:6379/0
            key_prefix: Key前缀，用于命名空间隔离
                示例："life:device-123" → 实际key为 "life:device-123:rhythm"
            ttl: 过期时间（秒），None表示永不过期
                建议：2592000（30天）

        Raises:
            ImportError: 如果redis包未安装
            redis.ConnectionError: 如果无法连接到Redis
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis backend requires 'redis' package. "
                "Install it with: pip install redis"
            )

        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl

        # 创建Redis连接
        try:
            self.client = redis.from_url(
                redis_url,
                decode_responses=True  # 自动解码为字符串
            )
            # 测试连接
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"无法连接到Redis: {e}") from e

    def _make_key(self, key: str) -> str:
        """生成完整的Redis key

        Args:
            key: 系统名称（�� "rhythm"）

        Returns:
            str: 完整key（如 "life:device-123:rhythm"）
        """
        return f"{self.key_prefix}:{key}"

    def load(self, key: str) -> Dict[str, Any]:
        """从Redis加载状态"""
        redis_key = self._make_key(key)
        data = self.client.get(redis_key)

        if data is None:
            return {}

        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            print(f"⚠️  警告：解析 {key} 状态失败: {e}")
            return {}

    def save(self, key: str, state: Dict[str, Any]) -> None:
        """保存状态到Redis"""
        redis_key = self._make_key(key)
        data = json.dumps(state, separators=(',', ':'))

        if self.ttl:
            # 设置TTL
            self.client.setex(redis_key, self.ttl, data)
        else:
            # 永不过期
            self.client.set(redis_key, data)

    def delete(self, key: str) -> None:
        """从Redis删除状态"""
        redis_key = self._make_key(key)
        self.client.delete(redis_key)

    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        redis_key = self._make_key(key)
        return bool(self.client.exists(redis_key))

    def delete_all(self) -> int:
        """删除此key_prefix下的所有状态

        Returns:
            int: 删除的key数量
        """
        pattern = f"{self.key_prefix}:*"
        keys = self.client.keys(pattern)

        if keys:
            return self.client.delete(*keys)
        return 0

    def __repr__(self) -> str:
        return f"<RedisStorage(prefix='{self.key_prefix}', ttl={self.ttl})>"
```

---

#### **state_manager.py（改造）**

```python
#!/usr/bin/env python3
"""
State Manager - 统一状态管理（支持多后端）

改造要点：
1. 支持backend参数选择存储后端
2. 保持API向后兼容
3. 支持延迟写入（auto_flush参数）
"""

from pathlib import Path
from typing import Dict, Any, Optional

from .storage_backend import StorageBackend
from .file_storage import FileStorage


class StateManager:
    """状态管理器（支持多后端）

    职责：
    1. 根据backend参数选择存储后端
    2. 提供统一的load/save接口
    3. 支持延迟写入优化
    """

    def __init__(
        self,
        backend: str = 'file',
        auto_flush: bool = True,
        **config
    ):
        """
        Args:
            backend: 存储后端类型
                - 'file': 文件存储（默认）
                - 'redis': Redis存储
            auto_flush: 是否自动写入
                - True: 每次save立即写入（默认）
                - False: 只在内存中保存，需手动flush()
            **config: 后端配置参数
                file后端:
                    - state_dir: 状态目录路径
                redis后端:
                    - redis_url: Redis连接字符串
                    - key_prefix: Key前缀（必需）
                    - ttl: 过期时间（秒，可选）

        示例:
            # 文件存储
            sm = StateManager(backend='file', state_dir='./data')

            # Redis存储
            sm = StateManager(
                backend='redis',
                redis_url='redis://localhost:6379/0',
                key_prefix='life:device-123',
                ttl=2592000  # 30天
            )
        """
        self.backend_type = backend
        self.auto_flush = auto_flush
        self._pending_saves: Dict[str, Dict[str, Any]] = {}

        # 创建存储后端
        if backend == 'file':
            state_dir = config.get('state_dir', '.')
            self.storage: StorageBackend = FileStorage(state_dir)

        elif backend == 'redis':
            from .redis_storage import RedisStorage

            redis_url = config.get('redis_url')
            key_prefix = config.get('key_prefix')
            ttl = config.get('ttl')

            if not redis_url:
                raise ValueError("redis_url is required for redis backend")
            if not key_prefix:
                raise ValueError("key_prefix is required for redis backend")

            self.storage = RedisStorage(redis_url, key_prefix, ttl)

        else:
            raise ValueError(f"Unknown backend: {backend}")

    def load(self, system_name: str) -> Dict[str, Any]:
        """加载状态

        优先返回pending中的数据（如果有）
        """
        # 如果有待写入的数据，直接返回
        if system_name in self._pending_saves:
            return self._pending_saves[system_name].copy()

        # 否则从存储后端加载
        return self.storage.load(system_name)

    def save(self, system_name: str, state: Dict[str, Any]) -> None:
        """保存状态

        根据auto_flush决定是否立即写入
        """
        if self.auto_flush:
            # 立即写入
            self.storage.save(system_name, state)
        else:
            # 延迟写入：只保存在内存中
            self._pending_saves[system_name] = state.copy()

    def flush(self) -> None:
        """将所有待写入的状态刷新到存储后端"""
        for system_name, state in self._pending_saves.items():
            self.storage.save(system_name, state)

        self._pending_saves.clear()

    def load_all(self, system_names: list[str]) -> Dict[str, Dict[str, Any]]:
        """批量加载多个系统的状态"""
        return {name: self.load(name) for name in system_names}

    def save_all(self, states: Dict[str, Dict[str, Any]]) -> None:
        """批量保存多个系统的状态"""
        for system_name, state in states.items():
            self.save(system_name, state)

    def reset(self, system_name: str) -> None:
        """重置指定系统的状态"""
        # 清除pending
        self._pending_saves.pop(system_name, None)
        # 删除存储
        self.storage.delete(system_name)

    def reset_all(self, system_names: list[str]) -> None:
        """批量重置系统状态"""
        for name in system_names:
            self.reset(name)

    def __repr__(self) -> str:
        return f"<StateManager(backend='{self.backend_type}', auto_flush={self.auto_flush})>"
```

---

#### **life.py（改造）**

```python
#!/usr/bin/env python3
"""
Life - 生命体主类（支持多存储后端）

改造要点：
1. 支持backend参数
2. 传递配置到StateManager
3. 新增flush()方法
"""

import time
from typing import Dict, Any

from core import StateManager, ProcessLock, BaseSystem
from systems import RhythmSystem, EnergySystem
from expression import ExpressionMapper


class Life:
    """数字生命体 - 支持多存储后端"""

    def __init__(
        self,
        # 存储后端配置
        backend: str = 'file',
        state_dir: str = None,
        redis_url: str = None,
        device_id: str = None,
        ttl: int = None,
        auto_flush: bool = True,
        # 其他配置
        time_scale: float = 1.0
    ):
        """初始化生命体

        Args:
            backend: 存储后端 ('file' | 'redis')
            state_dir: 文件存储目录（backend='file'时）
            redis_url: Redis连接字符串（backend='redis'时）
            device_id: 设备ID，用作Redis key前缀（backend='redis'时）
            ttl: Redis key过期时间（秒，backend='redis'时）
            auto_flush: 是否自动写入（False时需手动flush）
            time_scale: 时间加速倍数

        示例:
            # 文件存储（本地开发）
            life = Life(backend='file', state_dir='./data')

            # Redis存储（Server端）
            life = Life(
                backend='redis',
                redis_url=os.getenv('KV_URL'),
                device_id='device-123',
                ttl=2592000,  # 30天
                auto_flush=False  # 延迟写入
            )
        """
        from datetime import datetime

        # 构建StateManager配置
        if backend == 'file':
            config = {
                'state_dir': state_dir or '.',
                'auto_flush': auto_flush
            }
        elif backend == 'redis':
            if not redis_url:
                raise ValueError("redis_url is required for redis backend")
            if not device_id:
                raise ValueError("device_id is required for redis backend")

            config = {
                'redis_url': redis_url,
                'key_prefix': f"life:{device_id}",
                'ttl': ttl,
                'auto_flush': auto_flush
            }
        else:
            raise ValueError(f"Unknown backend: {backend}")

        # 初始化状态管��器
        self.state_manager = StateManager(backend=backend, **config)
        self.process_lock = ProcessLock(state_dir) if backend == 'file' else None

        # 初始化系统
        self.rhythm = RhythmSystem()
        self.energy = EnergySystem()

        self.systems: Dict[str, BaseSystem] = {
            "rhythm": self.rhythm,
            "energy": self.energy
        }

        # 运行状态
        self.running = False
        self.start_time = None
        self.time_scale = time_scale
        self.tick_count = 0

        # 生命体元信息
        self.birth_time = datetime.now()
        self.life_id = 1

        # 从存储恢复状态
        self._load_states()

    def flush(self) -> None:
        """手动刷新状态到存储后端

        在auto_flush=False模式下，必须调用此方法才会真正写入
        """
        self.state_manager.flush()

    def tick(self, dt: float = 1.0) -> None:
        """执行一次更新周期

        注意：
        - 如果auto_flush=True，每次tick都会写入存储
        - 如果auto_flush=False，需要手动调用flush()
        """
        # 计算从启动到现在的总时间（秒）
        elapsed_time = (time.time() - self.start_time) * self.time_scale

        # 获取所有系统的当前状态
        states = self.get_states()

        # 更新节律系统
        rhythm_context = {
            "current_state": states["rhythm"],
            "elapsed_time": elapsed_time
        }
        new_rhythm_state = self.rhythm.update(dt, rhythm_context)
        self.state_manager.save("rhythm", new_rhythm_state)

        # 刷新状态
        states = self.get_states()

        # 更新能量系统
        energy_context = {
            "current_state": states["energy"],
            "elapsed_time": elapsed_time,
            "other_systems": {"rhythm": states["rhythm"]}
        }
        new_energy_state = self.energy.update(dt, energy_context)
        self.state_manager.save("energy", new_energy_state)

        # 更新计数器
        self.tick_count += 1

    def stop(self) -> None:
        """停止生命体"""
        if not self.running:
            return

        self.running = False

        # 确保所有待写入的状态都被刷新
        self.flush()

        if self.process_lock:
            self.process_lock.release()

    # ... 其他方法保持不变
```

---

### 4.3 依赖管理

#### **pyproject.toml**

```toml
[project]
name = "micro-life-sim"
version = "0.4.0"  # 版本号提升
description = "A micro-scale autonomous AI life simulation"
requires-python = ">=3.10"

# 核心依赖（无外部依赖）
dependencies = []

# 可选依赖
[project.optional-dependencies]
redis = [
    "redis>=5.0.0"
]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "redis>=5.0.0"  # 开发时也需要测试Redis
]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## 5. 性能分析

### 5.1 基准测试场景

**场景**: 推进1440分钟（24小时）

| 后端 | auto_flush | tick次数 | 写入次数 | 总耗时 | 单次平均 |
|------|-----------|---------|---------|--------|---------|
| File | True | 1440 | 2880 | ~14.4秒 | ~10ms |
| Redis | True | 1440 | 2880 | ~1.4秒 | ~1ms |
| Redis | False | 1440 | 2 | ~11ms | ~0.008ms |

**结论**: Redis + 延迟写入可提升**1300倍**性能

---

### 5.2 并发性能估算

**100个并发请求，每个推进1440分钟**

| 后端 | 模式 | 总耗时 | 吞吐量 |
|------|------|--------|--------|
| File | auto_flush=True | ~24分钟 | 4 req/min |
| Redis | auto_flush=True | ~2.3分钟 | 43 req/min |
| Redis | auto_flush=False | ~1.1秒 | 5400 req/min |

**结论**: Redis延迟写入可支持**大规模并发**

---

### 5.3 资源消耗

#### **内存占用**

```
单个Life实例（auto_flush=False）:
├── RhythmSystem: ~500 bytes
├── EnergySystem: ~500 bytes
├── StateManager: ~200 bytes
├── pending_saves:
│   ├── rhythm: ~100 bytes
│   └── energy: ~100 bytes
└── 其他: ~600 bytes
────────────────────────────
总计: ~2 KB
```

**100个并发**: 2KB × 100 = **200KB** ✅

#### **网络I/O**

```
Redis延迟写入模式:
├── 每个Life实例: 2次Redis写入（rhythm + energy）
├── 100个并发: 200次Redis写入
├── 单次写入: ~1ms
└── 总耗时: ~200ms
────────────────────────────
可接受 ✅
```

---

## 6. 与pet-life-server集成

### 6.1 pet-life-server中的使用

```python
# src/life_adapter.py

import os
from life import Life
from typing import Dict

class LifeAdapter:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.redis_url = os.getenv('KV_URL')

    def get_state(self) -> Dict:
        """获取当前宠物状态"""

        # 创建Life实例（Redis后端，延迟写入）
        life = Life(
            backend='redis',
            redis_url=self.redis_url,
            device_id=self.device_id,
            ttl=2592000,  # 30天
            auto_flush=False  # 性能优化
        )

        # 启动（从Redis加载状态）
        life.start()

        # 计算时间差并推进
        minutes_elapsed = self._calculate_elapsed_minutes(life)

        for _ in range(minutes_elapsed):
            life.tick()

        # 刷新到Redis
        life.flush()

        # 获取原始数据
        states = life.get_states()

        life.stop()

        return {
            'energy': states['energy']['energy'],
            'rhythm_phase': states['rhythm']['internal_phase']
        }
```

### 6.2 API端点集成

```python
# api/index.py

@app.get("/api/pet/status")
async def get_pet_status(device_id: str):
    """获取宠物状态（自动推进时间）"""
    try:
        if not device_id:
            raise HTTPException(status_code=400, detail="device_id is required")

        adapter = LifeAdapter(device_id)
        life_raw_data = adapter.get_state()

        # 映射为宠物状态
        pet_state = map_to_pet_state(life_raw_data)

        return {
            "success": True,
            "data": pet_state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 7. 部署指南

### 7.1 Vercel部署配置

#### **配置Vercel KV**

```bash
# 1. 在Vercel项目中添加KV存储
vercel kv create

# 2. 关联到项目
vercel kv link

# 3. 查看环境变量
vercel env ls
# 应该看到 KV_URL、KV_REST_API_URL等
```

#### **requirements.txt**

```txt
fastapi==0.104.1
uvicorn==0.24.0
redis==5.0.1

# micro-life-sim（支持Redis）
git+https://${VERCEL_TOKEN}@github.com/DeeWooo/micro-life-sim.git#egg=micro-life-sim[redis]
```

#### **在pet-life-server中使用**

```python
# src/life_adapter.py

import os
from life import Life

class LifeAdapter:
    def __init__(self, device_id: str):
        self.device_id = device_id
        # 从环境变量读取Vercel KV连接
        self.kv_url = os.getenv('KV_URL')

        if not self.kv_url:
            raise ValueError("KV_URL environment variable not set")

    def create_life(self) -> Life:
        """创建Life实例"""
        return Life(
            backend='redis',
            redis_url=self.kv_url,
            device_id=self.device_id,
            ttl=2592000,  # 30天
            auto_flush=False  # 性能优化
        )
```

### 7.2 本地开发环境

```bash
# 1. 安装Redis（macOS）
brew install redis
brew services start redis

# 2. 安装micro-life-sim（含Redis支持）
cd micro-life-sim
pip install -e ".[redis]"

# 3. 测试
python -c "
from life import Life
life = Life(backend='redis', redis_url='redis://localhost:6379/0', device_id='dev-1')
life.start()
life.tick()
life.stop()
print('Redis backend works!')
"
```

---

## 8. 风险评估

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解方案 | 优先级 |
|------|------|------|----------|--------|
| **Redis连接失败** | 服务不可用 | 中 | 连接重试 + 降级到内存模式 | P0 |
| **Redis数据丢失** | 状态重置 | 低 | 定期备份 + TTL设置合理 | P1 |
| **Key冲突** | 数据污染 | 低 | 统一key_prefix规范 | P2 |
| **性能不达预期** | 响应慢 | 低 | 延迟写入 + Pipeline优化 | P1 |
| **向后兼容性** | 破坏现有功能 | 中 | 充分测试 + 默认file后端 | P0 |

---

### 8.2 运营风险

| 风险 | 影响 | 缓解方案 |
|------|------|----------|
| **Redis成本** | 增加运营成本 | Vercel KV有免费额度 |
| **数据泄露** | 安全问题 | Redis密码保护 + VPC隔离 |
| **调试困难** | 开发效率降低 | 提供Redis CLI查看工具 |

---

## 9. 待决策事项

### 9.1 高优先级

- [ ] **Redis依赖方式**：
  - 选项A：redis作为可选依赖（`pip install micro-life-sim[redis]`）
  - 选项B：redis作为核心依赖
  - **推荐**：选项A，保持micro-life-sim的轻量级

- [ ] **Key前缀规范**：
  - 当前设计：`life:{device_id}:{system_name}`
  - 是否需要调整？是否需要增加环境标识（如`prod/dev`）？

- [ ] **TTL默认值**：
  - 当前建议：2592000秒（30天）
  - 是否合理？需要调整吗？

---

### 9.2 中优先级

- [ ] **Pipeline优化**：
  - 是否需要支持Redis Pipeline批量写入？
  - 在延迟写入模式下，可以进一步优化为Pipeline

- [ ] **连接池配置**：
  - redis-py默认有连接池，是否需要暴露配置？
  - 如最大连接数、超时时间等

- [ ] **监控指标**：
  - 是否需要内置监控（如Redis写入次数、耗时）？
  - 还是由调用方自行实现？

---

### 9.3 低优先级

- [ ] **Redis Cluster支持**：
  - 当前只支持单实例Redis
  - 未来是否需要支持Cluster？

- [ ] **Pub/Sub支持**：
  - 是否需要支持Redis Pub/Sub实现实时通知？
  - 如状态变更推送到其他服务

- [ ] **备份恢复**：
  - 是否需要提供Redis数据导出/导入工具？
  - 用于数据备份和迁移

---

## 附录

### A. Redis Key设计详解

#### **完整Key格式**

```
{prefix}:{device_id}:{system_name}
```

#### **示例**

```redis
# 设备 device-123 的状态
life:device-123:rhythm    # 节律系统
life:device-123:energy    # 能量系统

# 设备 device-456 的状态
life:device-456:rhythm
life:device-456:energy
```

#### **Redis CLI操作**

```bash
# 查看某个设备的所有key
redis-cli KEYS "life:device-123:*"

# 查看rhythm状态
redis-cli GET "life:device-123:rhythm"

# 删除某个设备的所有数据
redis-cli DEL $(redis-cli KEYS "life:device-123:*" | xargs)

# 查看TTL
redis-cli TTL "life:device-123:rhythm"
```

---

### B. 性能基准测试脚本

```python
#!/usr/bin/env python3
"""
性能基准测试：对比不同存储后端的性能
"""

import time
from life import Life

def benchmark_file():
    """文件存储基准"""
    life = Life(backend='file', state_dir='/tmp/bench-file')
    life.start()

    start = time.time()
    for _ in range(1440):
        life.tick()
    elapsed = time.time() - start

    life.stop()
    print(f"File backend (auto_flush=True): {elapsed:.2f}s")


def benchmark_redis_auto():
    """Redis存储（自动写入）"""
    life = Life(
        backend='redis',
        redis_url='redis://localhost:6379/0',
        device_id='bench-auto',
        auto_flush=True
    )
    life.start()

    start = time.time()
    for _ in range(1440):
        life.tick()
    elapsed = time.time() - start

    life.stop()
    print(f"Redis backend (auto_flush=True): {elapsed:.2f}s")


def benchmark_redis_delayed():
    """Redis存储（延迟写入）"""
    life = Life(
        backend='redis',
        redis_url='redis://localhost:6379/0',
        device_id='bench-delayed',
        auto_flush=False
    )
    life.start()

    start = time.time()
    for _ in range(1440):
        life.tick()
    life.flush()
    elapsed = time.time() - start

    life.stop()
    print(f"Redis backend (auto_flush=False): {elapsed:.2f}s")


if __name__ == '__main__':
    print("Running benchmarks (1440 ticks)...")
    benchmark_file()
    benchmark_redis_auto()
    benchmark_redis_delayed()
```

---

### C. 修订历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2025-10-31 | Ivy & AI | 初始版本，Redis存储后端技术方案 |
| v1.1 | 2025-11-02 | Ivy & AI | 适配到pet-life-server项目，完善集成指南 |

---

**文档结束**