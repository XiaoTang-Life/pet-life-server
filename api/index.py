"""
Pet Life Server - FastAPI入口
在Vercel上部署的API服务
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sys
import os

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import PetState, InteractRequest, FeedRequest
from src.pet_adapter import PetAdapter

# 创建FastAPI应用
app = FastAPI(
    title="Pet Life Server",
    description="桌面宠物云端服务",
    version="0.1.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 基础健康检查 ====================

@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "service": "Pet Life Server",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== 宠物API ====================

@app.get("/api/pet/status")
async def get_pet_status(device_id: str):
    """
    获取宠物状态

    参数:
    - device_id: 设备ID (必需)
    """
    try:
        if not device_id:
            raise HTTPException(status_code=400, detail="device_id is required")

        adapter = PetAdapter(device_id)
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
    """
    宠物互动

    支持的action:
    - feed: 喂食
    - greet: 打招呼
    - play: 玩耍
    """
    try:
        if not request.device_id:
            raise HTTPException(status_code=400, detail="device_id is required")
        if not request.action:
            raise HTTPException(status_code=400, detail="action is required")

        adapter = PetAdapter(request.device_id)
        state = adapter.interact(request.action)

        return {
            "success": True,
            "action": request.action,
            "data": state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pet/feed")
async def feed_pet(request: FeedRequest):
    """
    喂食API（interact的简化版）
    """
    try:
        if not request.device_id:
            raise HTTPException(status_code=400, detail="device_id is required")

        adapter = PetAdapter(request.device_id)
        state = adapter.interact("feed")

        return {
            "success": True,
            "action": "feed",
            "data": state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 调试API ====================

@app.post("/api/debug/reset")
async def debug_reset(device_id: str):
    """
    重置宠物状态（调试用）
    """
    try:
        adapter = PetAdapter(device_id)
        state = adapter.reset()

        return {
            "success": True,
            "message": f"Pet {device_id} reset",
            "data": state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 错误处理 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Vercel需要的WSGI兼容性
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
