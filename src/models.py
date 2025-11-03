"""宠物数据模型"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PetState(BaseModel):
    """
    全局宠物状态
    
    架构变更：
    - 移除current_state字段（由客户端根据数值自行判断）
    - 所有用户共享同一份energy/hunger/mood数值
    - device_id仅用于追踪请求来源
    """
    device_id: str  # 请求来源设备ID
    energy: float   # 0-100，全局共享
    hunger: float   # 0-100，全局共享
    mood: float     # 0-100，全局共享
    last_updated: datetime
    pet_name: Optional[str] = "小糖"


class InteractRequest(BaseModel):
    """互动请求"""
    device_id: str
    action: str  # feed, greet, play, etc
    user_id: Optional[str] = None


class FeedRequest(BaseModel):
    """喂食请求"""
    device_id: str
    food_type: str = "normal"
    user_id: Optional[str] = None
