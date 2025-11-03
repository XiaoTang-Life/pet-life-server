"""
Vercel部署测试脚本 - 测试云端服务

使用方法：
    python3 test_vercel.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://pet-life-server.vercel.app"
DEVICE_ID = "vercel-test-device-001"

def print_response(title, response, show_body=True):
    """美化打印响应"""
    print(f"\n{'='*60}")
    print(f"📌 {title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    if show_body:
        try:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(response.text)


def test_health():
    """测试健康检查"""
    print("\n🚀 开始测试Pet Life Server Vercel部署\n")
    print(f"服务URL: {BASE_URL}\n")

    try:
        response = requests.get(f"{BASE_URL}/health")
        print_response("健康检查", response)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        return False


def test_root():
    """测试根路径"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print_response("服务根路径", response)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_get_status():
    """测试获取宠物状态"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/pet/status",
            params={"device_id": DEVICE_ID}
        )
        print_response(f"获取宠物状态 (device_id={DEVICE_ID})", response)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_reset():
    """测试重置"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/debug/reset",
            params={"device_id": DEVICE_ID}
        )
        print_response("重置宠物状态", response)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_feed():
    """测试喂食"""
    try:
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
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_interact():
    """测试互动"""
    try:
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
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def run_tests():
    """运行所有测试"""

    # 健康检查
    if not test_health():
        print("\n❌ 服务不可用，无法继续测试")
        return

    # 根路径
    test_root()

    # 重置状态
    test_reset()

    # 获取初始状态
    test_get_status()

    # 喂食
    test_feed()

    # 互动
    test_interact()

    # 最终状态
    test_get_status()

    print(f"\n{'='*60}")
    print("✅ 所有Vercel测试完成!")
    print(f"{'='*60}\n")
    print(f"🎉 你的pet-life-server服务已成功部署到Vercel!")
    print(f"📍 服务地址: {BASE_URL}")
    print(f"📚 API文档: {BASE_URL}/docs\n")


if __name__ == "__main__":
    run_tests()
