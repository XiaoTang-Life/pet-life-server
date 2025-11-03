# Pet Life Server

**Cloud service for xiaotang-life desktop pet | 小糖生命的云端服务**

```
┌─────────────────────────────────────────────────┐
│  Pet Life Server - C 纪元生产系统               │
│  ✅ 完成状态: C 纪元存储重构和部署              │
│  📅 最后更新: 2025-11-03                        │
│  🌐 在线服务: https://pet-life-server.vercel.app │
└─────────────────────────────────────────────────┘
```

---

## 📖 快速导航

### 🚀 快速开始

- **第一次使用？** → 阅读 [QUICKSTART.md](QUICKSTART.md)
- **想了解项目？** → 查看 [docs/README.md](docs/README.md)（文档导航中心）
- **想部署到 Vercel？** → 查看 [docs/Phase-5-Redis存储集成/Redis存储集成指南.md](docs/Phase-5-Redis存储集成/Redis存储集成指南.md)
- **想看测试结果？** → 查看 [docs/验证测试报告.md](docs/验证测试报告.md)

---

## 📚 项目概览

### 项目定义

**Pet Life Server** 是小糖生命（xiaotang-life）的云端服务平台，使用 [micro-life-sim](https://github.com/DeeWooo/micro-life-sim) 作为生命引擎核心，为 iOS/Android 客户端提供：

- 🐾 **实时宠物状态管理** - 通过微观生命模型计算
- 📱 **多设备支持** - 设备级别的独立状态管理
- 🌐 **云端数据同步** - Vercel Marketplace (Upstash) Redis 存储
- ⚡ **高性能计算** - 延迟刷盘优化，132.6 倍性能提升
- 🔄 **跨设备恢复** - 快速离线补偿（24h < 10ms）

### 当前阶段

| 项目 | 信息 | 备注 |
|------|------|------|
| **项目状态** | 🟢 C 纪元生产系统 | 完整重构完成 |
| **技术栈** | Python + FastAPI + Vercel Marketplace | 云端优先 |
| **存储方案** | Redis (Upstash/Marketplace) / FileStorage | 自动选择 |
| **性能** | 132.6 倍提升 | 关键优化完成 |
| **部署地址** | https://pet-life-server.vercel.app | 线上运行中 |

---

## 🗂️ 项目结构与文件组织规则

### 代码结构（**重要** - 保持整洁）

```
pet-life-server/
│
├── 📄 README.md                  # 项目主入口文档
├── 📄 QUICKSTART.md              # 快速开始指南
├── 📄 main.py                    # FastAPI 应用入口
├── 📄 requirements.txt           # Python 依赖
├── 📄 vercel.json                # Vercel 部署配置
│
├── 📂 src/                       # 源代码
│   ├── life_adapter.py           # Life 引擎适配层（Redis 支持）
│   ├── models.py                 # 数据模型定义
│   └── pet_adapter.py            # 宠物适配器
│
├── 📂 api/                       # Vercel API 路由
│   ├── __init__.py
│   └── index.py                  # API 入口
│
├── 📂 docs/                      # 📚 所有项目文档（详见下方规则）
│   ├── README.md                 # 文档导航中心 ⭐
│   ├── guides/                   # 📖 使用指南
│   │   ├── integration-guide.md  # 集成指南
│   │   ├── vercel-setup.md       # Vercel 部署
│   │   └── upstash-setup.md      # Upstash 安装
│   ├── references/               # 📝 参考文档
│   │   ├── upstash-quick-reference.md
│   │   └── upstash-integration-summary.md
│   ├── Phase-N-[功能名]/         # 阶段级文档
│   ├── 整体重构总结.md           # 项目级总结
│   └── 验证测试报告.md           # 项目级测试报告
│
├── 📂 tests/                     # 🧪 所有测试脚本
│   ├── test_api.py               # API 测试
│   ├── test_integration.py       # 集成测试
│   ├── test_redis_connection.py  # Redis 连接测试
│   └── test_vercel.py            # Vercel 部署测试
│
└── 📂 scripts/                   # 🔧 构建和部署脚本
    ├── build.sh                  # 构建脚本
    ├── build-alternative.sh      # 替代构建方案
    ├── install-deps.sh           # 安装依赖
    └── prepare-build.sh          # 准备构建
```

### 📋 文件组织规则（**强制执行**）

> ⚠️ **重要**：为了保持项目整洁，所有新建文件必须遵循规则。完整说明见：[FILE_ORGANIZATION_RULES.md](FILE_ORGANIZATION_RULES.md)

#### **✅ 根目录规则**

只允许放以下文件在根目录：

| 文件类型 | 允许的文件 | 说明 |
|---------|----------|------|
| **代码** | `main.py` | FastAPI 应用 |
| **配置** | `requirements.txt`, `vercel.json` | 项目配置 |
| **文档** | `README.md`, `QUICKSTART.md` | 仅这两个 |

❌ **禁止放在根目录**：
- ❌ 其他文档 → 移到 `docs/guides/` 或 `docs/references/`
- ❌ 测试脚本 → 移到 `tests/`
- ❌ 工具脚本 → 移到 `scripts/`

#### **📂 目录快速查询**

查看新文件应该放在哪里：

| 文件类型 | 目录 | 示例 |
|---------|------|------|
| 使用指南/教程 | `docs/guides/` | `integration-guide.md` |
| 参考文档/总结 | `docs/references/` | `upstash-quick-reference.md` |
| 阶段文档 | `docs/Phase-N-[功能]/` | Phase-6-用户认证/ |
| 测试脚本 | `tests/` | `test_api.py` |
| 构建脚本 | `scripts/` | `build.sh` |

#### **文档分层结构**

```
docs/
│
├── README.md ⭐ (总导航)
│   └─ 所有文档的入口，包含：
│      ├─ 按角色分类（开发者、架构师、PM）
│      ├─ 按时间顺序
│      ├─ 快速问题解答
│      └─ 维护规范说明
│
├── 整体重构总结.md (项目级文档)
│   └─ 整个项目的工作总结、成果展示、性能数据
│
├── 验证测试报告.md (项目级文档)
│   └─ 端到端验证结果、测试覆盖、质量指标
│
├── Phase-N-[功能名]/ ⭐ (阶段级文件夹)
│   │
│   ├── README.md (阶段导航)
│   │   └─ 该阶段的文档索引、工作流、成果总结
│   │
│   ├── 功能设计.md [日期]
│   │   └─ 该阶段的设计方案和技术方案
│   │
│   ├── 实施指南.md [日期]
│   │   └─ 部署、配置、使用说明
│   │
│   ├── 验证报告.md [日期]
│   │   └─ 测试结果、验收标准、性能数据
│   │
│   └── [其他阶段文档].md
│       └─ 根据具体阶段需要添加
│
└── ivy/ (研究与设计，已归档)
    └─ 规划期间的技术方案、架构设计等
```

#### **现有的阶段文件夹**

- **Phase-5-Redis存储集成/** (2025-11-02 ~ 2025-11-03)
  - Redis 和 Vercel KV 集成
  - LifeAdapter 重构
  - 性能优化和验证

#### **下一个阶段的命名规则**

创建新的阶段时，遵循以下规则：

```
Phase-6-[功能简称]/
  其中：
  - 编号递增（6, 7, 8, ...）
  - [功能简称] 用中文或英文描述，如：
    - Phase-6-用户认证
    - Phase-7-社交系统
    - Phase-8-性能优化

  包含的文档：
  ├── README.md                    # 阶段导航和概览
  ├── [功能名]-设计方案.md [日期]   # 技术方案
  ├── [功能名]-实施指南.md [日期]   # 部署手册
  ├── [功能名]-测试报告.md [日期]   # 验证结果
  └── [其他].md                    # 如需要
```

#### **文档头部标准格式**

每个文档的开头必须包含清晰的元数据：

```markdown
# 文档标题

**文档类型**: 项目级/阶段级
**项目**: XiaoTang-Life / pet-life-server
**阶段**: Phase N - [阶段描述]
**日期**: YYYY-MM-DD ~ YYYY-MM-DD （如有范围）
**完成日期**: YYYY-MM-DD
**状态**: ✅ 完成 / ⏳ 进行中 / 🔄 待更新
**版本**: v0.X.X （如适用）

> 一句话描述本文档的目的和内容

---
```

#### **文档维护规范**

1. **时间戳**
   - 每个文档都要标注日期
   - 若有重大更新，在头部更新日期

2. **交叉链接**
   - 上级文档链接到下级
   - 下级文档链接回上级
   - 相关文档相互链接

3. **导航 README**
   - 每个文件夹都要有 README.md
   - README 要列出该级别所有文档及其描述

4. **文档归档**
   - 完成的阶段不修改，保留在原位置
   - 规划期间的文档存放在 `ivy/` 目录

5. **搜索友好**
   - 使用明确的标题和分类
   - 在 README 中用表格列出所有文档
   - 包含快速问题解答部分

---

## 🎯 快速文档查找

### 按角色查找

**👨‍�� 我是开发者**
- 想本地运行？→ [QUICKSTART.md](QUICKSTART.md)
- 想部署到 Vercel？→ [docs/Phase-5-Redis存储集成/Redis存储集成指南.md](docs/Phase-5-Redis存储集成/Redis存储集成指南.md)
- 想了解 API？→ https://pet-life-server.vercel.app/docs
- 想看代码？→ [src/](src/)

**🏗️ 我是架构师**
- 想了解整体设计？→ [docs/整体重构总结.md](docs/整体重构总结.md)
- 想看技术方案？→ [docs/ivy/](docs/ivy/)
- 想了解性能数据？→ [docs/验证测试报告.md](docs/验证测试报告.md)

**📊 我是项目经理**
- 想要工作总结？→ [docs/整体重构总结.md](docs/整体重构总结.md)
- 想看质量报告？→ [docs/验证测试报告.md](docs/验证测试报告.md)
- 想看阶段成果？→ [docs/Phase-5-Redis存储集成/README.md](docs/Phase-5-Redis存储集成/README.md)

### 按时间查找

| 时间 | 文档 | 类型 |
|------|------|------|
| 2025-11-02 | Redis 存储集成指南 | Phase-5 实施 |
| 2025-11-02 | Phase5 完成总结 | Phase-5 总结 |
| 2025-11-03 | 集成测试记录 | Phase-5 测试 |
| 2025-11-03 | 验证测试报告 | 项目级测试 |
| 2025-11-03 | 整体重构总结 | 项目级总结 |

---

## 🚀 核心功能

### API 端点

| 端点 | 方法 | 说明 | 性能 |
|------|------|------|------|
| `/api/pet/status` | GET | 获取宠物状态 | < 10ms |
| `/api/pet/interact` | POST | 宠物交互（play/feed/greet） | < 5ms |
| `/api/pet/catchup` | POST | 离线快速补偿 | < 10ms |
| `/` | GET | 健康检查 | 立即 |
| `/health` | GET | 健康状态 | 立即 |

详细 API 文档：https://pet-life-server.vercel.app/docs

### 核心特性

- ✅ **多存储后端支持** - FileStorage (本地) / RedisStorage (云端)
- ✅ **自动环境选择** - 检测 KV_REST_API_URL 自动切换
- ✅ **延迟刷盘优化** - 132.6 倍性能提升
- ✅ **多设备隔离** - Redis 键空间隔离，完全独立
- ✅ **故障自动转移** - Redis 失败自动降级到文件存储
- ✅ **100% 向后兼容** - 0 breaking changes

---

## 📈 性能数据

| 操作 | 耗时 | 性能 | 说明 |
|------|------|------|------|
| 获取状态 | < 10ms | 快速 | API 响应 |
| 交互操作 | < 5ms | 极快 | 包含状态计算 |
| 24h 离线补偿 | < 10ms | 超快 | 延迟刷盘效果 |
| 1440 ticks 计算 | 5ms | 132.6x | vs 原来 0.639s |

---

## 🛠️ 开发指南

### 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 本地运行
python main.py
# 或
fastapi dev main.py

# 3. 访问
# - API: http://localhost:8000/docs
# - 根路由: http://localhost:8000/
```

### 运行测试

```bash
# 集成测试
python test_integration.py

# 所有测试应该 100% 通过
```

### 部署到 Vercel

```bash
# 1. 配置 KV 存储
#    在 Vercel Dashboard 创建 KV 存储
#    自动注入 KV_REST_API_URL 环境变量

# 2. 推送代码
git push origin main

# 3. Vercel 自动构建和部署
#    访问 https://your-project.vercel.app
```

详见：[docs/Phase-5-Redis存储集成/Redis存储集成指南.md](docs/Phase-5-Redis存储集成/Redis存储集成指南.md)

---

## 📦 依赖

### 核心依赖

```
fastapi==0.104.1          # Web 框架
uvicorn==0.24.0           # ASGI 服务器
pydantic==2.5.0           # 数据验证
python-dotenv==1.0.0      # 环境变量
redis>=5.0.0              # Redis 客户端（可选）
micro-life-sim@v0.4.0     # 生命引擎
```

### 可选依赖

- `redis` - 仅在使用 RedisStorage 时需要（Vercel 自动安装）

详见：[requirements.txt](requirements.txt)

---

## 🔗 相关项目

| 项目 | 说明 | 链接 |
|------|------|------|
| **micro-life-sim** | 生命引擎核心 | [GitHub](https://github.com/DeeWooo/micro-life-sim) |
| **XiaoTang-Life** | 整个项目组织 | [GitHub](https://github.com/DeeWooo/XiaoTang-Life) |
| **Pet-Widget** | iOS 客户端 | [GitHub](https://github.com/DeeWooo/Pet-Widget) |

---

## 📞 获取帮助

### 常见问题

**Q: 为什么要用 Redis？**
A: 支持 Serverless 部署（Vercel），本地开发自动用文件存储，无缝切换。

**Q: 本地开发需要 Redis 吗？**
A: 不需要，自动使用 FileStorage（文件存储）。

**Q: 如何部署到 Vercel？**
A: 按照 [Redis 存储集成指南](docs/Phase-5-Redis存储集成/Redis存储集成指南.md) 操作。

**Q: 性能真的提升了 132 倍吗？**
A: 是的，延迟刷盘模式的结果。详见 [验证测试报告](docs/验证测试报告.md)。

### 获取更多帮助

- **API 文档**: https://pet-life-server.vercel.app/docs
- **完整文档**: [docs/README.md](docs/README.md)
- **问题反馈**: GitHub Issues

---

## 📄 许可证

MIT License

---

## 🎯 接下来的工作

### 短期（下一个 Phase）

- [ ] 客户端集成（iOS/Android）
- [ ] 用户认证系统
- [ ] 实时通知功能

### 中期规划

- [ ] 社交系统（宠物互动）
- [ ] 多宠物支持
- [ ] 性能监控面板

### 长期愿景

- [ ] 群体行为模拟
- [ ] 进化和学习系统
- [ ] 数据分析和推荐

详见：[docs/ivy/产品演化路线图.md](docs/ivy/产品演化路线图.md)

---

**最后更新**: 2025-11-03
**维护者**: Claude Code
**项目状态**: 🟢 C 纪元生产就绪
**在线服务**: https://pet-life-server.vercel.app

