#!/usr/bin/env python3
"""
测试 Upstash Redis 连接

使用方法：
    python test_redis_connection.py
"""

import os
from dotenv import load_dotenv
import redis

# 加载环境变量
load_dotenv()
load_dotenv(".env.local", override=True)

def test_redis_connection():
    """测试 Redis 连接"""
    print("=" * 60)
    print("🔍 Upstash Redis 连接测试")
    print("=" * 60)

    redis_url = os.getenv("REDIS_URL")

    if not redis_url:
        print("❌ 错误：未找到 REDIS_URL 环境变量")
        print("   请确保 .env.local 文件中有 REDIS_URL 配置")
        return False

    print(f"\n📝 使用的 Redis URL:")
    # 隐藏密码显示
    url_display = redis_url.replace(
        redis_url.split("@")[0].split("://")[-1],
        "****:****"
    )
    print(f"   {url_display}")

    try:
        print("\n⏳ 尝试连接 Redis...")

        # 创建 Redis 连接（支持 rediss:// SSL）
        r = redis.from_url(redis_url, decode_responses=True)

        # 测试连接
        ping_result = r.ping()
        print(f"✅ 连接成功！Redis ping: {ping_result}")

        # 测试读写
        print("\n⏳ 测试读写操作...")
        test_key = "xiaotang-test-key"
        test_value = "Hello Upstash Redis!"

        # 写入
        r.set(test_key, test_value, ex=60)  # 60秒过期
        print(f"✅ 写入成功: {test_key} = {test_value}")

        # 读取
        retrieved = r.get(test_key)
        print(f"✅ 读取成功: {test_key} = {retrieved}")

        # 验证
        if retrieved == test_value:
            print("✅ 数据验证通过！")
        else:
            print(f"❌ 数据验证失败：期望 {test_value}，得到 {retrieved}")
            return False

        # 列出所有键
        print("\n⏳ 检查所有 Redis 键...")
        all_keys = r.keys("*")
        print(f"✅ 当前 Redis 中有 {len(all_keys)} 个键")
        if all_keys:
            print("   首 10 个键：")
            for key in all_keys[:10]:
                print(f"     - {key}")

        print("\n" + "=" * 60)
        print("🎉 所有测试通过！Upstash Redis 连接正常")
        print("=" * 60)
        return True

    except redis.ConnectionError as e:
        print(f"\n❌ 连接错误: {e}")
        print("\n   可能的原因：")
        print("   1. Redis URL 不正确")
        print("   2. Upstash 实例离线或被限制")
        print("   3. 网络连接问题")
        return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    exit(0 if success else 1)
