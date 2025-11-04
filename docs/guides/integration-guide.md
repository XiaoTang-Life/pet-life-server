# Pet Life Server - micro-life-sim集成指南

## 架构概述

pet-life-server通过以下方式集成micro-life-sim生命引擎：

```
┌─────────────────────────────────────┐
│   pet-life-server (FastAPI)         │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   LifeAdapter               │   │
│  │  (src/life_adapter.py)      │   │
│  │                             │   │
│  │ 职责：                       │   │
│  │ 1. 导入Life和ExpressionMapper│   │
│  │ 2. 管理多个设备的Life实例    │   │
│  │ 3. 映射内在状态到外显表达    │   │
│  │ 4. 提供API层接口             │   │
│  └──────────┬──────────────────┘   │
│             │                      │
│             ↓                      │
│  ┌──────────────────────────────┐  │
│  │ micro-life-sim (pip包)       │  │
│  │                              │  │
│  │ ├─ Life (生命体)             │  │
│  │ ├─ ExpressionMapper (表达)   │  │
│  │ ├─ RhythmSystem (节律)       │  │
│  │ └─ EnergySystem (能量)       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## 依赖管理

### requirements.txt

```
git+https://github.com/DeeWooo/micro-life-sim.git#egg=micro-life-sim
```

**说明：**
- 直接从GitHub安装micro-life-sim的最新版本
- 使用git URL而不是PyPI，方便快速迭代
- 未来可以改为PyPI版本：`micro-life-sim>=0.1.0`

## 导入机制

### 1. 本地开发环境

**路径结构：**
```
/Users/ivywu/Downloads/GitHub/Deewooo/
├── micro-life-sim/
│   └── src/
│       ├── life.py
│       ├── expression.py
│       ├── core/
│       └── systems/
└── XiaoTang-Life/
    └── pet-life-server/
        └── src/
            └── life_adapter.py
```

**导入过程（life_adapter.py）：**

```python
# 步骤1: 计算micro-life-sim的src路径
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(os.path.dirname(_current_dir))  # pet-life-server
_grandparent_dir = os.path.dirname(_parent_dir)  # Deewooo
MICRO_LIFE_SIM_PATH = os.path.join(_grandparent_dir, "micro-life-sim", "src")

# 步骤2: 将src路径添加到sys.path（仅本地开发）
if os.path.exists(MICRO_LIFE_SIM_PATH) and MICRO_LIFE_SIM_PATH not in sys.path:
    sys.path.insert(0, MICRO_LIFE_SIM_PATH)

# 步骤3: 导入Life引擎
try:
    from life import Life
    from expression import ExpressionMapper
    LIFE_ENGINE_AVAILABLE = True
except ImportError:
    LIFE_ENGINE_AVAILABLE = False
```

### 2. Vercel生产环境

**部署流程：**

1. `pip install -r requirements.txt` 安装所有依赖
2. micro-life-sim通过git URL从GitHub安装到site-packages
3. Python的import系统自动找到已安装的micro-life-sim包
4. life_adapter.py尝试添加本地src路径会失败（路径不存在），但不影响
5. 导入仍然成功（因为pip已经安装了包）

```python
# Vercel环境中的行为
MICRO_LIFE_SIM_PATH = "/tmp/xxx/micro-life-sim/src"  # 本地路径不存在
if os.path.exists(MICRO_LIFE_SIM_PATH):  # 返回False，跳过
    sys.path.insert(0, MICRO_LIFE_SIM_PATH)

# 但import仍然成功，因为pip已安装
from life import Life  # ✅ 从site-packages导入
```

## 为什么这样设计？

### ✅ 优点

1. **保持micro-life-sim纯粹**
   - micro-life-sim内部使用相对导入（`from expression import`）
   - 不需要修改micro-life-sim的代码

2. **本地开发友好**
   - 可以同时修改micro-life-sim和pet-life-server
   - 改动立即生效，无需重新安装

3. **生产环境兼容**
   - pip安装时自动处理依赖
   - 无需额外配置

4. **清晰的依赖关系**
   - requirements.txt明确指出依赖
   - 易于维护和升级

### ⚠️ 注意事项

1. **本地路径依赖**
   - 假设Deewooo目录结构不变
   - 如果移动目录，需要更新路径计算逻辑

2. **模块导入方式**
   - 不能用`from micro_life_sim import Life`（因为Life在src包下，而不是micro-life-sim包下）
   - 只能用`from life import Life`（通过sys.path）

## LifeAdapter的职责

### 核心功能

```python
class LifeAdapter:
    """生命引擎适配器"""

    def __init__(self, device_id: str):
        """为设备创建独立的Life实例"""
        self.life = Life(state_dir=f"/tmp/life-{device_id}")

    def get_state(self) -> Dict:
        """获取宠物的完整状态"""
        # 包括：
        # - internal_state: Life的节律、能量等
        # - expression: 脉动、色彩、感受、生命盒
        # - simplified_state: 派生的能量、饥饿、心情

    def interact(self, action: str) -> Dict:
        """处理用户交互（喂食、互动等）"""
```

### 多实例管理

```python
# 类级别的实例存储
_life_instances: Dict[str, Any] = {}      # device_id -> Life实例
_instance_metadata: Dict[str, Dict] = {}  # 元数据

# 每个设备独立演化
adapter1 = LifeAdapter("device-1")  # 创建第一个Life实例
adapter2 = LifeAdapter("device-2")  # 创建第二个Life实例
# 两个实例独立运行，互不影响
```

## API集成

### FastAPI端点

```python
# main.py
from src.life_adapter import LifeAdapter

@app.get("/api/pet/status")
async def get_pet_status(device_id: str):
    adapter = LifeAdapter(device_id)
    state = adapter.get_state()
    return {"success": True, "data": state}

@app.post("/api/pet/interact")
async def interact_pet(request: InteractRequest):
    adapter = LifeAdapter(request.device_id)
    state = adapter.interact(request.action)
    return {"success": True, "data": state}
```

### 响应示例

```json
{
  "internal_state": {
    "rhythm": {
      "internal_phase": 0.0,
      "last_update": 1761888237.943288
    },
    "energy": {
      "energy": 100.0
    }
  },
  "expression": {
    "pulse_rate": 95,
    "pulse_symbol": "●●●●●",
    "pulse_intensity": "极强",
    "color_hex": "#FFD700",
    "feeling": "晍晚渐近，但仍有充足的能量"
  },
  "simplified_state": {
    "energy": 50.0,
    "hunger": 50.0,
    "mood": 95.0,
    "current_state": "bored"
  }
}
```

## 部署检查清单

部署到Vercel前，确保：

- [ ] micro-life-sim已推送到GitHub
- [ ] requirements.txt包含git URL
- [ ] life_adapter.py能正确处理本地和远程环境
- [ ] 本地测试通过
- [ ] API端点正常工作

## 故障排查

### 问题：ImportError: No module named 'life'

**原因：** sys.path未正确配置，且pip包未安装

**解决：**
1. 本地开发：确保micro-life-sim/src目录存在且路径计算正确
2. Vercel：确保requirements.txt包含git URL，运行`pip install -r requirements.txt`

### 问题：生产环境Life导入失败

**原因：** 可能pip安装过程中出错

**解决：**
1. 检查Vercel日志
2. 手动测试：`python3 -c "from life import Life"`
3. 尝试重新部署

## 未来优化

1. **PyPI发布**
   - 将micro-life-sim发布到PyPI
   - 改为���`micro-life-sim>=0.1.0`

2. **模块结构优化**
   - 考虑将micro-life-sim重构为标准包形式
   - 支持`from micro_life_sim import Life`

3. **缓存优化**
   - 在Vercel KV中存储Life状态
   - 避免频繁重新初始化Life实例

4. **性能监控**
   - 监控Life引擎的计算时间
   - 优化Serverless函数冷启动
