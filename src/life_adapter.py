"""生命引擎适配器 - 将micro-life-sim的Life适配为宠物行为系统

架构思路：
- micro-life-sim 是独立的Python包，提供纯粹的生命引擎
- LifeAdapter 负责：
  1. 导入并使用micro-life-sim的Life和ExpressionMapper
  2. 将Life的内在状态映射到外显表达（脉动、色彩、感受）
  3. 管理多个设备的生命实例
  4. 将微观生命的抽象状态转换为宠物系统可理解的数据

导入方式说明：
- micro-life-sim的src目录通过sys.path添加，使其模块可直接导入
- 这样可以保持micro-life-sim的内部模块结构（相对导入）
- 同时避免修改micro-life-sim的内部代码以支持包的形式导入
- 对于Vercel部署，micro-life-sim会通过pip安装，sys.path会自动配置
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# 添加micro-life-sim的src路径以支持本地开发
# 在Vercel部署时，micro-life-sim会通过pip正确安装，这个路径添加不会有害
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(os.path.dirname(_current_dir))  # pet-life-server
_grandparent_dir = os.path.dirname(_parent_dir)  # Deewooo
MICRO_LIFE_SIM_PATH = os.path.join(_grandparent_dir, "micro-life-sim", "src")

# 仅在本地路径存在时添加（本地开发）
if os.path.exists(MICRO_LIFE_SIM_PATH) and MICRO_LIFE_SIM_PATH not in sys.path:
    sys.path.insert(0, MICRO_LIFE_SIM_PATH)

Life = None
ExpressionMapper = None
RedisStorage = None
LIFE_ENGINE_AVAILABLE = False

try:
    from life import Life
    from expression import ExpressionMapper
    from core import RedisStorage
    LIFE_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import micro-life-sim: {e}")
    LIFE_ENGINE_AVAILABLE = False


class LifeAdapter:
    """
    生命引擎适配器 - 使用真实的micro-life-sim引擎

    职责：
    1. 管理每个设备对应的Life实例
    2. 提供周期性的状态更新
    3. 将Life的内在状态映射到宠物的外显属性
    4. 处理用户交互（喂食、互动等）
    """

    # 宠物状态常量（从expression推导）
    STATE_SLEEP = "sleep"
    STATE_HUNGRY = "hungry"
    STATE_PLAY = "play"
    STATE_IDLE = "idle"
    STATE_BORED = "bored"
    STATE_GRUMPY = "grumpy"
    STATE_SLEEPY = "sleepy"

    # 生命实例管理
    _life_instances: Dict[str, Any] = {}  # 使用Any避免Life未定义的问题
    _instance_metadata: Dict[str, Dict[str, Any]] = {}

    def __init__(self, device_id: str):
        """
        初始化设备对应的生命适配器

        Args:
            device_id: 设备标识符
        """
        self.device_id = device_id

        if not LIFE_ENGINE_AVAILABLE:
            raise RuntimeError(
                "micro-life-sim engine not available. "
                "Please ensure it's properly installed."
            )

        self._ensure_life_exists()

    def _ensure_life_exists(self):
        """确保该设备对应的Life实例存在"""
        if self.device_id not in self._life_instances:
            # 为每个设备创建独立的Life实例
            # 优先使用Redis存储（Serverless环境）
            backend = self._create_storage_backend()

            life_instance = Life(
                backend=backend,
                time_scale=1.0,  # 正常速度
                auto_flush=False  # 使用延迟刷盘优化性能
            )

            # 启动Life实例（Redis模式下无需ProcessLock）
            life_instance.start()

            self._life_instances[self.device_id] = life_instance

            # 记录元数据
            self._instance_metadata[self.device_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "pet_name": "小糖",
                "device_id": self.device_id,
            }

    def _create_storage_backend(self):
        """创建存储后端（优先Redis，降级到文件）"""
        # 尝试从环境变量获取Redis配置
        # - REDIS_URL: Vercel Marketplace (Upstash) 或本地 Redis 实例
        # - KV_REST_API_URL: 旧版 Vercel KV (已弃用，但保留兼容性)
        redis_url = os.getenv("REDIS_URL") or os.getenv("KV_REST_API_URL")

        if redis_url and RedisStorage:
            # 使用Redis存储（Serverless环境）
            try:
                return RedisStorage(
                    redis_url=redis_url,
                    key_prefix=f"life_{self.device_id}",  # 按设备隔离
                    ttl=86400 * 7  # 7天过期
                )
            except Exception as e:
                print(f"Warning: Redis init failed, falling back to file storage: {e}")

        # 降级：使用文件存储（本地开发）
        state_dir = f"/tmp/life-{self.device_id}"
        from core import FileStorage
        return FileStorage(state_dir)

    def get_life(self) -> Life:
        """获取当前设备的Life实例"""
        self._ensure_life_exists()
        return self._life_instances[self.device_id]

    def get_state(self) -> Dict[str, Any]:
        """
        获取宠物当前状态

        Returns:
            包含内在状态和外显表达的字典
        """
        life = self.get_life()

        # 获取Life的内在状态
        life_states = life.get_states()
        expression = life.get_expression()
        metadata = self._instance_metadata[self.device_id]

        # 映射到宠物系统的状态格式
        pet_state = {
            "device_id": self.device_id,
            "pet_name": metadata["pet_name"],

            # 内在状态（来自Life引擎）
            "internal_state": {
                "rhythm": life_states.get("rhythm", {}),
                "energy": life_states.get("energy", {}),
            },

            # 外显表达（来自ExpressionMapper）
            "expression": {
                "pulse_rate": expression.get("pulse_rate"),
                "pulse_symbol": expression.get("pulse_symbol"),
                "pulse_intensity": expression.get("pulse_intensity"),
                "color_hex": expression.get("color_hex"),
                "color_name": expression.get("color_name"),
                "feeling": expression.get("feeling"),
                "life_box": expression.get("life_box"),
            },

            # 派生状态（用于简化的宠物UI）
            "simplified_state": self._derive_simplified_state(
                life_states,
                expression
            ),

            "last_updated": datetime.utcnow().isoformat(),
        }

        return pet_state

    def _derive_simplified_state(
        self,
        life_states: Dict[str, Any],
        expression: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从Life的状态派生出简化的宠物状态

        这是为了兼容产品文档中定义的宠物状态系统
        """
        # 简化的状态映射：从脉动频率和感受推导
        pulse_rate = expression.get("pulse_rate", 60)
        feeling = expression.get("feeling", "")

        # 简化为三个维度的数值（0-100），用于产品UI
        # 这里是示例实现，可以根据实际需求调整
        energy_value = self._extract_energy_value(life_states)
        hunger_value = self._extract_hunger_value(life_states)
        mood_value = self._extract_mood_value(expression)

        # 根据数值判断当前状态
        current_state = self._determine_state(
            energy_value,
            hunger_value,
            mood_value
        )

        return {
            "energy": energy_value,
            "hunger": hunger_value,
            "mood": mood_value,
            "current_state": current_state,
            "pulse_rate": pulse_rate,
            "feeling": feeling,
        }

    def _extract_energy_value(self, life_states: Dict) -> float:
        """从Life状态提取能量值（0-100）"""
        energy_state = life_states.get("energy", {})
        # 假设Life内部有energy_level字段
        value = energy_state.get("energy_level", 50)
        return max(0, min(100, float(value)))

    def _extract_hunger_value(self, life_states: Dict) -> float:
        """从Life状态提取饥饿值（0-100）"""
        # 在当前的Life实现中，可能没有直接的hunger字段
        # 这里作为示例，返回一个计算值
        energy_state = life_states.get("energy", {})
        energy_level = energy_state.get("energy_level", 50)

        # 简化规则：能量低时饥饿高
        hunger_value = 100 - energy_level
        return max(0, min(100, float(hunger_value)))

    def _extract_mood_value(self, expression: Dict) -> float:
        """从表达信息提取心情值（0-100）"""
        # 脉动强度可以用来反映心情
        pulse_intensity = expression.get("pulse_intensity", "中")

        intensity_map = {
            "极强": 95,
            "强": 80,
            "中": 60,
            "弱": 40,
            "微弱": 20,
        }
        mood_value = intensity_map.get(pulse_intensity, 50)
        return float(mood_value)

    def _determine_state(
        self,
        energy: float,
        hunger: float,
        mood: float
    ) -> str:
        """根据数值判断宠物状态"""
        # 优先级：饥饿 > 能量 > 心情
        if hunger >= 70:
            return self.STATE_HUNGRY

        if energy <= 30:
            if hunger >= 50:
                return self.STATE_SLEEPY
            return self.STATE_SLEEP

        if mood <= 30:
            return self.STATE_GRUMPY

        if energy >= 70 and mood >= 70:
            return self.STATE_PLAY

        if energy <= 50:
            return self.STATE_BORED

        return self.STATE_IDLE

    def interact(self, action: str) -> Dict[str, Any]:
        """
        处理用户互动

        Args:
            action: 互动类型（feed, greet, play等）

        Returns:
            更新后的宠物状态
        """
        life = self.get_life()

        # 这里可以根据action调用Life的不同操作
        # 当前示例中，我们简单地执行一次tick
        # 实际应用中可能需要修改Life类以支持交互反馈

        if action == "feed":
            # 简化实现：执行一次更新
            # 实际应该增加能量值
            pass
        elif action == "greet":
            # 互动应该增加心情
            pass
        elif action == "play":
            # 玩耍消耗能量，增加心情
            pass

        # 执行一个时间步的更新
        life.tick(dt=1.0)

        # 延迟刷盘模式下，需要手动刷盘
        # （这是为了优化Serverless环境的性能）
        if not life.state_manager.auto_flush:
            life.flush()

        return self.get_state()

    def reset(self) -> Dict[str, Any]:
        """重置宠物状态"""
        if self.device_id in self._life_instances:
            self._life_instances[self.device_id].reset()

        # 重新初始化元数据
        self._instance_metadata[self.device_id] = {
            "created_at": datetime.utcnow().isoformat(),
            "pet_name": "小糖",
            "device_id": self.device_id,
        }

        return self.get_state()

    def catchup(self, hours: int = 24) -> Dict[str, Any]:
        """
        快速补偿（用于离线恢复）

        当用户离线多小时后，执行快速补偿来计算宠物的状态变化
        利用延迟刷盘的性能优势，批量执行大量tick操作

        Args:
            hours: 需要补偿的小时数（默认24小时）

        Returns:
            更新后的宠物状态
        """
        life = self.get_life()

        # 批量执行tick（充分利用延迟刷盘的性能优势）
        # 132倍性能提升意味着可以快速处理1440个tick
        tick_count = hours
        for _ in range(tick_count):
            life.tick(dt=1.0)

        # 一次性刷盘到存储
        if not life.state_manager.auto_flush:
            life.flush()

        return self.get_state()

    @classmethod
    def cleanup(cls, device_id: str):
        """清理特定设备的Life实例"""
        if device_id in cls._life_instances:
            del cls._life_instances[device_id]
        if device_id in cls._instance_metadata:
            del cls._instance_metadata[device_id]
