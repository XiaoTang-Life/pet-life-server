"""宠物数据模型"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PetState(BaseModel):
    """宠物状态"""
    device_id: str
    energy: float  # 0-100
    hunger: float  # 0-100
    mood: float    # 0-100
    current_state: str  # sleep, hungry, play, idle, bored, grumpy, sleepy
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
