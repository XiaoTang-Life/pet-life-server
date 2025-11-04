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
import threading
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
    生命引擎适配器 - 全局共享宠物模式
    
    架构变更：
    - 所有用户共享同一个Life实例（全局单例）
    - device_id仅用于追踪互动来源和日志记录
    - 状态判断由客户端完成，Server只提供数值
    
    职责：
    1. 管理全局唯一的Life实例
    2. 提供全局共享的能量/饥饿/心情数值
    3. 处理用户交互并影响全局状态
    4. 记录互动来源以便分析
    """

    # 全局单例Life实例
    _global_life: Optional[Any] = None  # 全局共享的Life实例
    _global_life_lock = threading.Lock()  # 线程安全锁
    _global_metadata: Dict[str, Any] = {}  # 全局元数据
    
    # 全局宠物ID（固定）
    GLOBAL_PET_ID = "global_pet"

    def __init__(self, device_id: str):
        """
        初始化生命适配器
        
        注意：device_id仅用于日志记录和追踪互动来源，
        所有设备共享同一个Life实例

        Args:
            device_id: 设备标识符（用于追踪来源）
        """
        print(f"🔧 [LifeAdapter] 初始化开始, device_id={device_id}")
        self.device_id = device_id

        if not LIFE_ENGINE_AVAILABLE:
            print("❌ [LifeAdapter] Life引擎不可用")
            raise RuntimeError(
                "micro-life-sim engine not available. "
                "Please ensure it's properly installed."
            )

        print(f"✅ [LifeAdapter] Life引擎可用，开始确保全局实例存在")
        self._ensure_global_life_exists()
        print(f"✅ [LifeAdapter] 初始化完成, device_id={device_id}")

    def _ensure_global_life_exists(self):
        """
        确保全局Life实例存在（线程安全）
        
        使用双重检查锁定模式（Double-Checked Locking）
        确保多线程环境下只创建一次实例
        """
        if self.__class__._global_life is None:
            with self.__class__._global_life_lock:
                # Double-check：避免多线程重复创建
                if self.__class__._global_life is None:
                    # 创建全局存储后端
                    backend = self._create_storage_backend()

                    # 创建全局Life实例
                    life_instance = Life(
                        backend=backend,
                        time_scale=1.0,  # 正常速度
                        auto_flush=False  # 使用延迟刷盘优化性能
                    )

                    # 启动Life实例
                    life_instance.start()

                    # 赋值给类变量
                    self.__class__._global_life = life_instance

                    # 初始化全局元数据
                    self.__class__._global_metadata = {
                        "created_at": datetime.utcnow().isoformat(),
                        "pet_name": "小糖",
                        "global_pet_id": self.GLOBAL_PET_ID,
                        "shared_mode": True,
                    }
                    
                    print(f"✅ [LifeAdapter] 全局Life实例已创建: {self.GLOBAL_PET_ID}")

    def _create_storage_backend(self):
        """
        创建全局存储后端（优先Redis，降级到文件）
        
        注意：使用固定的key_prefix确保所有设备访问同一份数据
        """
        print("🔍 [Storage] 开始创建存储后端...")
        
        # 尝试从环境变量获取Redis配置
        # - REDIS_URL: Vercel Marketplace (Upstash) 或本地 Redis 实例
        # - KV_REST_API_URL: 旧版 Vercel KV (已弃用，但保留兼容性)
        redis_url = os.getenv("REDIS_URL") or os.getenv("KV_REST_API_URL")
        
        print(f"🔍 [Storage] REDIS_URL={'存在' if os.getenv('REDIS_URL') else '不存在'}")
        print(f"🔍 [Storage] KV_REST_API_URL={'存在' if os.getenv('KV_REST_API_URL') else '不存在'}")
        print(f"🔍 [Storage] RedisStorage={'可用' if RedisStorage else '不可用'}")

        if redis_url and RedisStorage:
            # 使用Redis存储（Serverless环境）
            print(f"✅ [Storage] 使用Redis存储，key_prefix=life_{self.GLOBAL_PET_ID}")
            try:
                backend = RedisStorage(
                    redis_url=redis_url,
                    key_prefix=f"life_{self.GLOBAL_PET_ID}",  # 全局固定前缀
                    ttl=86400 * 30  # 30天过期（全局宠物需要更长保留）
                )
                print("✅ [Storage] Redis存储初始化成功")
                return backend
            except Exception as e:
                print(f"⚠️  [Storage] Redis初始化失败，降级到文件存储: {e}")
                import traceback
                print(f"⚠️  [Storage] 错误详情: {traceback.format_exc()}")

        # 降级：使用文件存储（本地开发）
        state_dir = f"/tmp/life-{self.GLOBAL_PET_ID}"
        print(f"⚠️  [Storage] 使用文件存储（降级模式），目录={state_dir}")
        from core import FileStorage
        return FileStorage(state_dir)

    def get_life(self) -> Life:
        """
        获取全局Life实例
        
        Returns:
            全局共享的Life实例
        """
        return self.__class__._global_life

    def get_state(self) -> Dict[str, Any]:
        """
        获取全局宠物当前状态
        
        注意：返回的是全局共享的数值，不包含具体状态
        具体状态由客户端根据数值自行判断

        Returns:
            包含全局共享数值的字典
        """
        life = self.get_life()

        # 获取Life的内在状态
        life_states = life.get_states()
        expression = life.get_expression()
        metadata = self.__class__._global_metadata

        # 映射到宠物系统的状态格式
        pet_state = {
            "device_id": self.device_id,  # 请求来源设备
            "pet_name": metadata["pet_name"],
            "global_pet_id": self.GLOBAL_PET_ID,

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

            # 简化数值（用于客户端决策）
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
        从Life的状态派生出简化的数值
        
        架构变更：
        - 只返回数值（energy/hunger/mood）
        - 不再判断具体状态（由客户端决定）
        - 客户端使用这些数值影响RefreshStrategy的概率
        """
        # 提取三个核心数值（0-100）
        energy_value = self._extract_energy_value(life_states)
        hunger_value = self._extract_hunger_value(life_states)
        mood_value = self._extract_mood_value(expression)

        # 额外的表达信息（可选，用于丰富客户端体验）
        pulse_rate = expression.get("pulse_rate", 60)
        feeling = expression.get("feeling", "")

        return {
            # 核心数值（客户端用于决策）
            "energy": energy_value,
            "hunger": hunger_value,
            "mood": mood_value,
            
            # 辅助信息（客户端可选使用）
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


    def interact(self, action: str) -> Dict[str, Any]:
        """
        处理用户互动（影响全局状态）
        
        架构变更：
        - 任何用户的互动都会影响全局宠物状态
        - 记录互动来源以便分析

        Args:
            action: 互动类型（feed, greet, play等）

        Returns:
            更新后的全局宠物状态
        """
        life = self.get_life()

        # 记录互动日志（用于追踪和分析）
        print(f"🎮 [Interact] device={self.device_id}, action={action}, timestamp={datetime.utcnow().isoformat()}")

        # 根据action执行不同的操作
        # TODO: 未来可以扩展Life引擎以支持更细粒度的交互
        if action == "feed":
            # 喂食：执行更新
            print(f"  🍕 喂食操作 by {self.device_id}")
        elif action == "greet":
            # 打招呼：增加互动
            print(f"  👋 打招呼 by {self.device_id}")
        elif action == "play":
            # 玩耍：消耗能量，增加心情
            print(f"  🎾 玩耍 by {self.device_id}")

        # 执行一个时间步的更新
        life.tick(dt=1.0)

        # 延迟刷盘模式下，需要手动刷盘
        # （这是为了优化Serverless环境的性能）
        if not life.state_manager.auto_flush:
            life.flush()

        return self.get_state()

    def reset(self) -> Dict[str, Any]:
        """
        重置全局宠物状态
        
        注意：这会影响所有用户！仅用于调试
        """
        print(f"⚠️  [Reset] 全局宠物状态重置 by device={self.device_id}")
        
        life = self.get_life()
        if life:
            life.reset()

        # 重新初始化全局元数据
        self.__class__._global_metadata = {
            "created_at": datetime.utcnow().isoformat(),
            "pet_name": "小糖",
            "global_pet_id": self.GLOBAL_PET_ID,
            "shared_mode": True,
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
    def cleanup_global(cls):
        """
        清理全局Life实例
        
        注意：这会影响所有用户！仅用于维护或测试
        """
        with cls._global_life_lock:
            if cls._global_life:
                print("⚠️  [Cleanup] 清理全局Life实例")
                cls._global_life = None
                cls._global_metadata = {}
