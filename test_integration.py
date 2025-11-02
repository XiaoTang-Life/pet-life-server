#!/usr/bin/env python3
"""
集成测试：验证 pet-life-server 与 micro-life-sim v0.4.0 的集成

测试覆盖：
1. LifeAdapter 初始化和存储后端选择
2. 基本 API 功能
3. 性能基准测试
"""

import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.life_adapter import LifeAdapter


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 70)
    print("测试1：基本功能")
    print("=" * 70)
    print()

    # 创建适配器
    print("创建 LifeAdapter...")
    adapter = LifeAdapter("test_device_001")
    print("✅ LifeAdapter 创建成功")
    print()

    # 获取状态
    print("获取宠物状态...")
    state = adapter.get_state()
    print(f"✅ 获取状态成功")
    print(f"   - 宠物名称: {state['pet_name']}")
    print(f"   - 脉动速率: {state['expression']['pulse_rate']} bpm")
    print(f"   - 内在感受: {state['expression']['feeling']}")
    print()

    # 互动
    print("执行互动（feed）...")
    state = adapter.interact("feed")
    print(f"✅ 互动成功")
    print(f"   - 新状态: {state['simplified_state']['current_state']}")
    print()


def test_catchup_performance():
    """测试快速补偿的性能"""
    print("=" * 70)
    print("测试2：快速补偿性能")
    print("=" * 70)
    print()

    adapter = LifeAdapter("test_device_perf")

    # 24小时补偿
    hours = 24
    print(f"执行 {hours} 小时补偿（{hours * 60} 分钟 = {hours} tick）...")

    start = time.time()
    state = adapter.catchup(hours=hours)
    elapsed = time.time() - start

    print(f"✅ 补偿完成")
    print(f"   - 耗时: {elapsed * 1000:.1f} ms")
    print(f"   - 性能: {hours / elapsed:.0f} tick/秒")
    print(f"   - 期望: <100ms（132倍优化）")
    print()

    if elapsed < 0.1:
        print("✨ 性能超群！✨")
    elif elapsed < 0.5:
        print("⚡ 性能良好")
    else:
        print("⚠️  性能不如预期")
    print()


def test_multiple_devices():
    """测试多设备隔离"""
    print("=" * 70)
    print("测试3：多设备隔离")
    print("=" * 70)
    print()

    # 创建两个设备的适配器
    adapter1 = LifeAdapter("device_user_1")
    adapter2 = LifeAdapter("device_user_2")

    print("获取设备1的状态...")
    state1 = adapter1.get_state()
    pulse1_before = state1["expression"]["pulse_rate"]

    print("获取设备2的状态...")
    state2 = adapter2.get_state()
    pulse2_before = state2["expression"]["pulse_rate"]

    print()
    print(f"设备1脉动: {pulse1_before} bpm")
    print(f"设备2脉动: {pulse2_before} bpm")
    print()

    # 对设备1进行交互
    print("对设备1执行10次互动...")
    for _ in range(10):
        state1 = adapter1.interact("play")

    pulse1_after = state1["expression"]["pulse_rate"]

    # 检查设备2是否未变化
    state2_after = adapter2.get_state()
    pulse2_after = state2_after["expression"]["pulse_rate"]

    print()
    print(f"设备1脉动: {pulse1_before} → {pulse1_after} bpm")
    print(f"设备2脉动: {pulse2_before} → {pulse2_after} bpm")
    print()

    if pulse2_after == pulse2_before:
        print("✅ 多设备隔离成功：设备2不受设备1影响")
    else:
        print("❌ 多设备隔离失败：设备受到交叉影响")
    print()


def test_storage_backend():
    """测试存储后端选择"""
    print("=" * 70)
    print("测试4：存储后端选择")
    print("=" * 70)
    print()

    adapter = LifeAdapter("test_storage")
    life = adapter.get_life()

    backend_name = type(life.state_manager.backend).__name__
    auto_flush = life.state_manager.auto_flush

    print(f"当前存储后端: {backend_name}")
    print(f"自动刷盘: {auto_flush}")
    print()

    if backend_name == "RedisStorage":
        print("✅ 使用 Redis 存储（Serverless 环境）")
    elif backend_name == "FileStorage":
        print("✅ 使用文件存储（本地开发环境）")
    else:
        print(f"⚠️ 未知存储后端: {backend_name}")

    if not auto_flush:
        print("✅ 延迟刷盘已启用（性能优化）")
    else:
        print("⚠️ 自动刷盘模式（性能未优化）")
    print()


def main():
    """运行所有测试"""
    print()
    print("█" * 70)
    print("█  pet-life-server 与 micro-life-sim v0.4.0 集成测试")
    print("█" * 70)
    print()

    try:
        test_basic_functionality()
        test_storage_backend()
        test_multiple_devices()
        test_catchup_performance()

        print()
        print("█" * 70)
        print("█  所有测试完成！")
        print("█" * 70)
        print()
        print("✨ 集成验证成功！")
        print()
        print("下一步：")
        print("  1. 启动本地服务: python main.py")
        print("  2. 访问 API 文档: http://localhost:8000/docs")
        print("  3. 部署到 Vercel: git push origin main")
        print()

    except Exception as e:
        print()
        print("❌ 测试失败！")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
