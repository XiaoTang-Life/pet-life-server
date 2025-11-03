# Upstash Redis 快速参考指南

**日期**: 2025-11-03
**项目**: Pet Life Server

---

## 🔍 在 Upstash 控制台查看数据

### 当前数据状态

```
📊 已存储 5 个键：
✓ life_test-device-001:energy      (宠物能量状态)
✓ life_test-device-001:rhythm      (宠物脉动状态)
✓ pet:test-device-001:info         (宠物信息)
✓ pet:test-device-001:last-update  (最后更新时间)
✓ test:sample                       (测试数据)
```

### 方法 1: 使用 REPL (CLI) 查看数据 ⭐ 推荐

1. **登录 Upstash 控制台**: https://console.upstash.com
2. **进入你的数据库**: xiaotang-life-redis
3. **点击左侧菜单 "REPL"** (Redis CLI)
4. **输入命令查看所有键**:
   ```
   KEYS *
   ```
   返回：
   ```
   1) "life_test-device-001:energy"
   2) "life_test-device-001:rhythm"
   3) "pet:test-device-001:info"
   4) "pet:test-device-001:last-update"
   5) "test:sample"
   ```

5. **查看具体的值**:
   ```
   GET test:sample
   ```
   返回：
   ```
   "Hello from pet-life-server!"
   ```

6. **查看 JSON 数据**:
   ```
   GET pet:test-device-001:info
   ```
   返回：
   ```json
   {
     "device_id": "test-device-001",
     "pet_name": "小糖",
     "energy": 95.5,
     "mood": 85.0,
     "timestamp": "2025-11-03T02:35:00"
   }
   ```

### 方法 2: 使用 Data Browser 查看数据

1. **登录 Upstash 控制台**: https://console.upstash.com
2. **进入你的数据库**: xiaotang-life-redis
3. **点击左侧菜单 "Data Browser"** 或 "Browse"
4. **在搜索框输入**:
   - `*` - 查看所有键
   - `test:*` - 查看所有 test 前缀的键
   - `life_*` - 查看所有 life 前缀的键
5. **点击 "Search"** 查看结果

### 方法 3: 使用本地 Python 脚本查看数据 ✅ 已验证

```bash
python3 test_redis_connection.py
```

输出示例：
```
🔍 Upstash Redis 连接测试
✅ 连接成功！Redis ping: True
✅ 当前 Redis 中有 5 个键
   首 10 个键：
     - life_test-device-001:energy
     - life_test-device-001:rhythm
     - pet:test-device-001:info
     - pet:test-device-001:last-update
     - test:sample
```

---

## 📝 常用 Redis 命令

在 Upstash REPL 中使用：

### 查看数据

```redis
# 查看所有键
KEYS *

# 查看特定前缀的键
KEYS pet:*
KEYS life_*

# 查看键的个数
DBSIZE

# 获取值
GET <key>

# 查看键的类型
TYPE <key>

# 查看键的过期时间（-1 表示永不过期）
TTL <key>
```

### 写入数据

```redis
# 设置值
SET <key> <value>

# 设置值并指定过期时间（秒）
SET <key> <value> EX 3600

# 增加数值
INCR <key>

# 删除键
DEL <key>

# 清空所有数据（谨慎使用！）
FLUSHDB
```

### 监控

```redis
# 查看服务器信息
INFO

# 查看连接数
CLIENT LIST

# 查看最近的命令
COMMAND DOCS
```

---

## 🚀 测试宠物 API

### 1. 获取宠物状态

```bash
curl "http://localhost:8000/api/pet/status?device_id=test-device-001" | python3 -m json.tool
```

**返回数据**:
- `device_id`: 设备 ID
- `pet_name`: 宠物名称（小糖）
- `internal_state`: 内在状态（脉动、能量）
- `expression`: 外显表达（脉动率、颜色、感受）
- `simplified_state`: 简化状态（能量、饥饿、心情）

### 2. 与宠物互动

```bash
curl -X POST 'http://localhost:8000/api/pet/interact' \
  -H 'Content-Type: application/json' \
  -d '{"device_id": "test-device-001", "action": "play"}'
```

支持的 action：
- `feed` - 喂食
- `play` - 玩耍
- `greet` - 打招呼

### 3. 快速补偿（离线恢复）

```bash
curl -X POST 'http://localhost:8000/api/pet/catchup?device_id=test-device-001&hours=24'
```

---

## 🔐 安全和最佳实践

### ✅ 已做好的

- [x] `.env.local` 包含敏感信息（不应提交到 Git）
- [x] REDIS_URL 在 `.env.local` 中本地管理
- [x] 使用 `rediss://` SSL 加密连接
- [x] Upstash 免费版足够测试和小规模使用

### ⚠️ 生产环境建议

1. **不要提交 `.env.local` 到 Git**
   ```bash
   # 添加到 .gitignore
   echo ".env.local" >> .gitignore
   ```

2. **在 Vercel 设置环境变量**
   - 通过 Vercel 控制台或 Marketplace 集成
   - 不要在代码中硬编码敏感信息

3. **定期检查使用情况**
   - 监控 Upstash 仪表板
   - 查看命令数和存储大小
   - 设置告警（如接近限制）

4. **备份重要数据**
   - Upstash 提供导出功能
   - 定期备份到本地或其他存储

---

## 📊 Upstash 仪表板导览

### Status 选项卡
- **Status**: 数据库状态（Available/Unavailable）
- **Created**: 创建时间
- **Plan**: 当前计划（Free/Pro）
- **Current Period**: 当前周期的使用量

### Quickstart 选项卡
- 显示不同语言的连接示例
- `.env.local` - 环境变量格式
- `Python` - Python 客户端示例
- `redis-cli` - Redis CLI 命令
- `cURL` - HTTP REST API 示例

### Usage 选项卡
- 显示命令数
- 显示存储大小
- **注意**: Usage 数据有延迟，不是实时的

### Data Browser 选项卡
- 浏览所有键值对
- 搜索和过滤
- 编辑值

### REPL 选项卡
- Redis 命令行界面
- 实时执行命令
- 查看结果

### Settings 选项卡
- 数据库配置
- 连接信息
- 账单信息

---

## ✅ 验证清单

✅ **已完成**:
- [x] Upstash Redis 数据库创建（xiaotang-life-redis）
- [x] 本地 `.env.local` 配置
- [x] 环境变量加载配置
- [x] Redis 连接测试通过
- [x] 宠物 API 测试通过
- [x] 数据写入 Upstash 成功
- [x] 5 个测试键存储在 Redis

⏳ **待完成**:
- [ ] 推送代码到 GitHub
- [ ] 在 Vercel Marketplace 配置 Upstash
- [ ] 部署到 Vercel 并验证
- [ ] 监控生产环境

---

## 🆘 故障排查

### Q: 为什么 Usage 选项卡显示 "No data available"？
**A**: Usage 统计有延迟，通常需要等待几分钟更新。使用 REPL 或 Data Browser 实时查看数据。

### Q: 如何知道数据确实存储了？
**A**:
1. 使用 REPL 执行 `KEYS *` 命令
2. 或使用本地 `test_redis_connection.py` 脚本验证
3. 或在 Data Browser 中搜索键

### Q: 数据会自动删除吗？
**A**:
- 设置了 TTL (过期时间) 的键会自动删除
- 没有设置 TTL 的键永久存储
- 可以使用 `TTL <key>` 命令查看

### Q: 如何清空所有数据？
**A**: 在 REPL 执行 `FLUSHDB` (谨慎使用！)

---

## 📚 相关文档

- [Upstash 完整安装指南](UPSTASH_SETUP.md)
- [Upstash 集成总结](UPSTASH_INTEGRATION_SUMMARY.md)
- [Redis 存储集成指南](docs/Phase-5-Redis存储集成/Redis存储集成指南.md)
- [Upstash 官方文档](https://upstash.com/docs/redis)

---

**最后更新**: 2025-11-03
**作者**: Claude Code
**状态**: ✅ 已验证
