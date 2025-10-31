"""宠物行为适配器 - 将生命引擎适配为宠物行为"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import json


class PetAdapter:
    """
    宠物适配器 - 管理宠物状态和行为

    MVP版本：简单的本地状态管理
    - 存储在内存中
    - 根据时间差推演状态
    """

    # 状态常量
    STATE_SLEEP = "sleep"
    STATE_HUNGRY = "hungry"
    STATE_PLAY = "play"
    STATE_IDLE = "idle"
    STATE_BORED = "bored"
    STATE_GRUMPY = "grumpy"
    STATE_SLEEPY = "sleepy"

    # 全局宠物状态存储（MVP阶段）
    _pet_states: Dict[str, Dict] = {}

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._ensure_pet_exists()

    def _ensure_pet_exists(self):
        """确保宠物状态存在"""
        if self.device_id not in self._pet_states:
            self._pet_states[self.device_id] = {
                "device_id": self.device_id,
                "energy": 80.0,
                "hunger": 30.0,
                "mood": 70.0,
                "current_state": self.STATE_IDLE,
                "last_updated": datetime.utcnow().isoformat(),
                "pet_name": "小糖",
            }

    def get_state(self) -> Dict:
        """获取宠物当前状态"""
        self._ensure_pet_exists()
        state = self._pet_states[self.device_id].copy()

        # 补算时间差产生的状态变化
        state = self._calculate_delta(state)

        return state

    def _calculate_delta(self, state: Dict) -> Dict:
        """根据时间差补算状态变化"""
        last_updated = datetime.fromisoformat(state["last_updated"])
        now = datetime.utcnow()
        delta_minutes = (now - last_updated).total_seconds() / 60

        if delta_minutes <= 0:
            return state

        # 简单的每分钟规则（MVP版本）
        # 这里应该根据时间段采用不同的速率
        energy_change = delta_minutes * (-0.1)  # 每分钟消耗0.1
        hunger_change = delta_minutes * 0.15    # 每分钟增加0.15
        mood_change = delta_minutes * (-0.05)   # 每分钟减少0.05

        state["energy"] = max(0, min(100, state["energy"] + energy_change))
        state["hunger"] = max(0, min(100, state["hunger"] + hunger_change))
        state["mood"] = max(0, min(100, state["mood"] + mood_change))
        state["last_updated"] = now.isoformat()

        # 更新状态机
        state["current_state"] = self._determine_state(state)

        # 保存更新后的状态
        self._pet_states[self.device_id] = state

        return state

    def _determine_state(self, state: Dict) -> str:
        """根据数值确定宠物状态"""
        energy = state["energy"]
        hunger = state["hunger"]
        mood = state["mood"]

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

    def interact(self, action: str) -> Dict:
        """宠物互动"""
        state = self.get_state()

        if action == "feed":
            state["hunger"] = max(0, state["hunger"] - 30)
            state["energy"] = max(0, state["energy"] - 5)
            state["mood"] = min(100, state["mood"] + 10)

        elif action == "greet":
            state["mood"] = min(100, state["mood"] + 5)
            state["energy"] = max(0, state["energy"] - 2)

        elif action == "play":
            if state["energy"] > 30 and state["hunger"] < 70:
                state["energy"] = max(0, state["energy"] - 20)
                state["hunger"] = min(100, state["hunger"] + 10)
                state["mood"] = min(100, state["mood"] + 15)

        state["last_updated"] = datetime.utcnow().isoformat()
        state["current_state"] = self._determine_state(state)

        self._pet_states[self.device_id] = state

        return state

    def reset(self) -> Dict:
        """重置宠物状态（调试用）"""
        self._pet_states[self.device_id] = {
            "device_id": self.device_id,
            "energy": 80.0,
            "hunger": 30.0,
            "mood": 70.0,
            "current_state": self.STATE_IDLE,
            "last_updated": datetime.utcnow().isoformat(),
            "pet_name": "小糖",
        }
        return self._pet_states[self.device_id]
