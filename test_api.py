"""
API测试脚本 - 用来验证服务工作正常

使用方法：
1. 先启动服务: fastapi dev main.py
2. 在另一个终端运行: python test_api.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
DEVICE_ID = "test-iphone-123"

def print_response(title, response):
    """美化打印响应"""
    print(f"\n{'='*50}")
    print(f"📌 {title}")
    print(f"{'='*50}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print(f"状态码: {response.status_code}")


def test_health():
    """测试健康检查"""
    print("\n🚀 开始测试Pet Life Server API\n")

    try:
        response = requests.get(f"{BASE_URL}/health")
        print_response("健康检查", response)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print(f"   请确保服务已启动: fastapi dev main.py")
        return False


def test_get_status():
    """测试获取宠物状态"""
    response = requests.get(
        f"{BASE_URL}/api/pet/status",
        params={"device_id": DEVICE_ID}
    )
    print_response(f"获取宠物状态 (device_id={DEVICE_ID})", response)
    return response.status_code == 200


def test_feed():
    """测试喂食"""
    payload = {
        "device_id": DEVICE_ID,
        "food_type": "normal"
    }
    response = requests.post(
        f"{BASE_URL}/api/pet/feed",
        json=payload
    )
    print_response("喂食", response)
    return response.status_code == 200


def test_interact():
    """测试互动"""
    payload = {
        "device_id": DEVICE_ID,
        "action": "greet"
    }
    response = requests.post(
        f"{BASE_URL}/api/pet/interact",
        json=payload
    )
    print_response("打招呼互动", response)
    return response.status_code == 200


def test_play():
    """测试玩耍"""
    payload = {
        "device_id": DEVICE_ID,
        "action": "play"
    }
    response = requests.post(
        f"{BASE_URL}/api/pet/interact",
        json=payload
    )
    print_response("玩耍互动", response)
    return response.status_code == 200


def test_reset():
    """测试重置"""
    response = requests.post(
        f"{BASE_URL}/api/debug/reset",
        params={"device_id": DEVICE_ID}
    )
    print_response("重置宠物状态", response)
    return response.status_code == 200


def run_tests():
    """运行所有测试"""

    # 健康检查
    if not test_health():
        return

    # 重置状态
    test_reset()

    # 获取初始状态
    test_get_status()

    # 喂食
    test_feed()

    # 互动
    test_interact()
    test_play()

    # 最终状态
    test_get_status()

    print(f"\n{'='*50}")
    print("✅ 所有测试完成!")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run_tests()
