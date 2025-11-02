# Server为真源架构方案

**文档状态**: 草案  
**创建日期**: 2025-10-31  
**最后更新**: 2025-11-01 (v0.3 - 全局共享模式)  
**作者**: Ivy & AI Assistant  

> **重大变更 v0.3**：产品策略调整为**所有用户共享一个小糖**，架构从"多设备隔离"改为"全局单例"。  

---

## 📋 目录

- [1. 架构决策](#1-架构决策)
- [2. 职责划分](#2-职责划分)
- [3. 核心设计](#3-核心设计)
- [4. 数据模型](#4-数据模型)
- [5. 关键问题解答](#5-关键问题解答)
- [6. Server端实现](#6-server端实现)
- [7. iOS端实现](#7-ios端实现)
- [8. 潜在风险](#8-潜在风险)
- [9. 待讨论事项](#9-待讨论事项)

---

## 1. 架构决策

### 1.1 核心原则

**Server是唯一真源（Single Source of Truth）+ 全局共享宠物**

- ✅ 生命引擎（micro-life-sim）运行在Server端
- ✅ **所有用户共享一个小糖**（全局单例）
- ✅ 状态计算和推进由Server的定时任务负责
- ✅ iOS端负责缓存、展示和用户交互
- ✅ 用户交互立即影响全局状态

### 1.2 为什么选择全局共享模式？

|| 优势 | 说明 |
||------|------|
|| **资源消耗O(1)** | 无论多少用户，只维护1个Life实例 |
|| **真正的主动行为** | 定时任务持续推进，可实时发推送 |
|| **社交化体验** | 用户共同养育一个小糖，互动可见 |
|| **成本可控** | 不随用户数增长，适合MVP验证 |
|| **简化架构** | 无需处理多实例并发和隔离 |

### 1.3 为什么选择Server为真源？

| 优势 | 说明 |
|------|------|
| **状态一致性** | 避免多端各自计算导致状态不一致 |
| **逻辑统一** | 引擎逻辑只需维护一份（Python） |
| **跨平台支持** | 未来可支持Android、Web等平台 |
| **数据安全** | 状态数据集中管理，便于备份和恢复 |
| **算力集中** | 复杂计算在Server完成，减轻客户端负担 |

### 1.3 权衡与限制

| 限制 | 影响 | 缓解方案 |
|------|------|----------|
| **Widget刷新延迟** | 用户看到的可能是几分钟前的状态 | 显示"更新于X分钟前"提示 |
| **网络依赖** | 离线时无法获取最新状态 | 使用本地缓存 + 离线提示 |
| **API调用成本** | 频繁请求可能产生费用 | 合理控制拉取频率 |
| **Server冷启动** | 首次请求可能有1-2秒延迟 | 优化Vercel配置 + 超时处理 |

---

## 2. 职责划分

### 2.1 架构图（分层职责）

```
┌─────────────────────────────────────────────┐
│     micro-life-sim (生命基础设施)            │
│                                             │
│  职责：                                     │
│  - 节律系统 (RhythmSystem)                  │
│  - 能量系统 (EnergySystem)                  │
│  - 脉动表达 (ExpressionMapper)              │
│                                             │
│  输出（原始数据）：                          │
│  - energy: 0-100                            │
│  - rhythm_phase: 0-1                        │
│  - pulse_rate: 60-120                       │
│  - color_hex, feeling                       │
└─────────────────────────────────────────────┘
                    ↓ 原始数据
┌─────────────────────────────────────────────┐
│          Server（唯一真源）                   │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │  pet-life-server (产品适配层)       │    │
│  │                                    │    │
│  │  ├─ LifeAdapter                    │    │
│  │  │  └─ 调用micro-life-sim          │    │
│  │  │                                 │    │
│  │  ├─ PetStateMapper                 │    │
│  │  │  └─ 映射能量/饥饿/心情           │    │
│  │  │                                 │    │
│  │  ├─ StateMachine                   │    │
│  │  │  └─ 判断7种宠物状态              │    │
│  │  │                                 │    │
│  │  └─ QuoteGenerator                 │    │
│  │     └─ 生成宠物语录                 │    │
│  └────────────────────────────────────┘    │
│                    ↓                        │
│  ┌────────────────────────────────────┐    │
│  │  Vercel KV (Redis持久化)            │    │
│  │  Key: pet:{device_id}               │    │
│  │  Value: PetState (JSON)             │    │
│  │  - 跨请求状态保持                   │    │
│  │  - TTL: 30天无访问自动清理           │    │
│  └────────────────────────────────────┘    │
│                    ↓                        │
│  ┌────────────────────────────────────┐    │
│  │  FastAPI (RESTful API)              │    │
│  │  - GET  /api/pet/status             │    │
│  │  - POST /api/pet/interact           │    │
│  │  - POST /api/pet/feed               │    │
│  │  - POST /api/debug/reset            │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                    ↕️  HTTPS
┌─────────────────────────────────────────────┐
│          iOS端（缓存+展示层）                 │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │  App (主应用)                       │    │
│  │  职责：                             │    │
│  │  - 定期拉取Server状态 (30-60s)      │    │
│  │  - 乐观更新UI（立即反馈）            │    │
│  │  - 互动时调用Server API             │    │
│  │  - 缓存状态到App Group              │    │
│  │  - 处理离线/超时场景                │    │
│  └────────────────────────────────────┘    │
│                    ↓                        │
│  ┌────────────────────────────────────┐    │
│  │  App Group (共享容器)                │    │
│  │  - 存储最后一次成功的PetState        │    │
│  │  - Widget和App共享读取              │    │
│  └────────────────────────────────────┘    │
│                    ↓                        │
│  ┌────────────────────────────────────┐    │
│  │  Widget (只读展示)                  │    │
│  │  职责：                             │    │
│  │  - 读取App Group缓存                │    │
│  │  - 系统允许时刷新UI                 │    │
│  │  - 点击唤起App                      │    │
│  │  限制：                             │    │
│  │  - ❌ 不能直接请求网络              │    │
│  │  - ❌ 刷新频率由系统控制（≈15分钟）  │    │
│  └────────────────────────────────────┘    │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │  Watch (可选，M0.9实现)              │    │
│  │  - 从iPhone通过WatchConnectivity    │    │
│  │    同步缓存数据                     │    │
│  │  - 只读展示，不运行引擎              │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### 2.2 职责清单（更新：明确分层边界）

| 层级 | 组件 | 职责 | 不做什么 |
|------|------|------|----------|
| **基础设施层** | **micro-life-sim** | • 节律系统（昼夜循环）<br>• 能量系统（生命能量）<br>• 脉动表达（pulse/color/feeling）<br>• 时间推进（tick） | • ❌ 不管"饥饿"概念<br>• ❌ 不判断7种宠物状态<br>• ❌ 不生成语录<br>• ❌ 不处理互动逻辑 |
| **产品适配层** | **pet-life-server** | • 调用micro-life-sim获取原始数据<br>• 映射能量/饥饿/心情（PetStateMapper）<br>• 判断7种宠物状态（StateMachine）<br>• 生成语录（QuoteGenerator）<br>• 持久化到Vercel KV<br>• 提供RESTful API | • ❌ 不直接推送到iOS<br>• ❌ 不管理iOS端UI逻辑 |
| **客户端层** | **iOS App** | • 定期拉取Server状态<br>• 缓存到App Group<br>• 乐观更新UI<br>• 处理用户交互 | • ❌ 不运行引擎计算<br>• ❌ 不做状态推进<br>• ❌ 不解决冲突（以Server为准） |
| **客户端层** | **Widget** | • 读取App Group缓存<br>• 展示宠物状态<br>• 提供交互入口 | • ❌ 不请求网络<br>• ❌ 不运行引擎<br>• ❌ 不修改状态 |
| **客户端层** | **Watch** | • 从iPhone同步数据<br>• 展示状态 | • ❌ 不直接请求Server<br>• ❌ 不运行引擎 |

---

## 3. 核心设计

### 3.1 Server端：时间推进机制

**核心思想**：每次API调用时，计算距离上次更新的时间差，推进引擎状态

```python
def get_pet_state(device_id: str) -> Dict:
    """获取宠物状态（自动推进时间）"""
    
    # 1. 从Vercel KV加载状态
    state = kv.get(f"pet:{device_id}")
    
    if not state:
        # 首次访问，创建初始状态
        state = create_initial_state(device_id)
        kv.set(f"pet:{device_id}", state)
        return state
    
    # 2. 计算时间差（分钟）
    now = datetime.utcnow()
    last_update = datetime.fromisoformat(state['last_calculated_at'])
    minutes_elapsed = (now - last_update).total_seconds() / 60
    
    # 3. 如果超过1分钟，推进引擎
    if minutes_elapsed >= 1:
        # 加载Life引擎
        life = Life.from_snapshot(state['engine_snapshot'])
        
        # 推进时间
        life.advance_minutes(int(minutes_elapsed))
        
        # 更新状态
        state['energy'] = life.get_energy()
        state['hunger'] = life.get_hunger()
        state['mood'] = life.get_mood()
        state['current_state'] = life.get_state()
        state['widget_quote'] = life.get_quote()
        state['expression'] = life.get_expression()
        state['engine_snapshot'] = life.to_snapshot()
        
        # 更新时间和版本号
        state['last_calculated_at'] = now.isoformat()
        state['version'] += 1
        
        # 保存回KV
        kv.set(f"pet:{device_id}", state)
    
    return state
```

**关键点**：
- ✅ 状态保存在Vercel KV，跨请求保持
- ✅ 每次请求时自动计算时间差
- ✅ 按分钟推进，避免频繁小步推进
- ✅ 版本号自增，便于调试和追踪

### 3.2 iOS端：缓存与拉取策略

#### 3.2.1 App前台拉取

```swift
class PetStateManager: ObservableObject {
    @Published var currentState: PetSnapshot?
    @Published var isLoading: Bool = false
    @Published var isOffline: Bool = false
    
    private var pollingTimer: Timer?
    private let apiClient: PetAPIClient
    private let appGroupStorage: AppGroupStorage
    
    // MARK: - 定期拉取
    
    func startPolling() {
        // App进入前台，立即拉取一次
        Task {
            await fetchFromServer()
        }
        
        // 然后每30秒拉取一次
        pollingTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task {
                await self?.fetchFromServer()
            }
        }
    }
    
    func stopPolling() {
        pollingTimer?.invalidate()
        pollingTimer = nil
    }
    
    // MARK: - 拉取状态
    
    func fetchFromServer() async {
        isLoading = true
        
        do {
            // 从Server获取状态
            let state = try await apiClient.getPetStatus(deviceId: DeviceID.current)
            
            // 更新本地状态
            await MainActor.run {
                self.currentState = state
                self.isOffline = false
            }
            
            // 写入App Group（供Widget读取）
            appGroupStorage.save(state)
            
        } catch {
            print("Failed to fetch from server: \(error)")
            
            // 网络错误，使用本地缓存
            if let cachedState = appGroupStorage.load() {
                await MainActor.run {
                    self.currentState = cachedState
                    self.isOffline = true
                }
            }
        }
        
        isLoading = false
    }
}
```

#### 3.2.2 乐观更新

```swift
extension PetStateManager {
    func interact(action: String) async {
        guard var state = currentState else { return }
        
        // 1. 乐观更新UI（立即反馈）
        state = optimisticUpdate(state: state, action: action)
        await MainActor.run {
            self.currentState = state
        }
        
        // 2. 异步调用Server
        do {
            let newState = try await apiClient.interact(
                deviceId: DeviceID.current,
                action: action
            )
            
            // 3. 以Server返回为准（覆盖乐观更新）
            await MainActor.run {
                self.currentState = newState
                self.isOffline = false
            }
            
            // 4. 更新App Group
            appGroupStorage.save(newState)
            
        } catch {
            print("Interact failed: \(error)")
            // 保留乐观更新的结果，下次拉取时会被Server状态覆盖
        }
    }
    
    private func optimisticUpdate(state: PetSnapshot, action: String) -> PetSnapshot {
        var newState = state
        
        switch action {
        case "feed":
            newState.hunger = max(0, state.hunger - 20)
            newState.mood = min(100, state.mood + 10)
        case "play":
            newState.mood = min(100, state.mood + 15)
            newState.energy = max(0, state.energy - 10)
        default:
            break
        }
        
        return newState
    }
}
```

#### 3.2.3 超时处理

```swift
extension PetAPIClient {
    func getPetStatus(deviceId: String) async throws -> PetSnapshot {
        let request = URLRequest(url: URL(string: "\(baseURL)/api/pet/status?device_id=\(deviceId)")!)
        
        // 5秒超时
        let (data, response) = try await URLSession.shared.data(for: request, timeout: 5.0)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        let result = try JSONDecoder().decode(APIResponse<PetSnapshot>.self, from: data)
        return result.data
    }
}

// 超时扩展
extension URLSession {
    func data(for request: URLRequest, timeout: TimeInterval) async throws -> (Data, URLResponse) {
        try await withThrowingTaskGroup(of: (Data, URLResponse).self) { group in
            group.addTask {
                try await self.data(for: request)
            }
            
            group.addTask {
                try await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
                throw URLError(.timedOut)
            }
            
            let result = try await group.next()!
            group.cancelAll()
            return result
        }
    }
}
```

### 3.3 Widget：只读展示

```swift
struct PetWidgetProvider: TimelineProvider {
    let appGroupStorage = AppGroupStorage()
    
    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> ()) {
        // 1. 从App Group读取缓存
        guard let state = appGroupStorage.load() else {
            // 没有缓存，显示占位符
            let entry = PetWidgetEntry(date: Date(), state: nil)
            let timeline = Timeline(entries: [entry], policy: .never)
            completion(timeline)
            return
        }
        
        // 2. 创建Timeline Entry
        let entry = PetWidgetEntry(
            date: Date(),
            state: state
        )
        
        // 3. 下次刷新时间（15分钟后，系统可能不保证）
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 15, to: Date())!
        
        let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
        completion(timeline)
    }
}

struct PetWidgetView: View {
    let entry: PetWidgetEntry
    
    var body: some View {
        if let state = entry.state {
            VStack(spacing: 8) {
                // 宠物状态
                Text(state.currentState)
                    .font(.title2)
                
                // 数值
                HStack {
                    StatusBar(label: "能量", value: state.energy, color: .blue)
                    StatusBar(label: "饥饿", value: state.hunger, color: .orange)
                    StatusBar(label: "心情", value: state.mood, color: .green)
                }
                
                // 语录
                Text(state.widgetQuote)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                // 更新时间提示
                Text("更新于 \(timeAgo(state.updatedAt))")
                    .font(.caption2)
                    .foregroundColor(.gray)
            }
            .padding()
        } else {
            // 占位符
            Text("打开App查看宠物")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
    
    private func timeAgo(_ date: Date) -> String {
        let minutes = Int(Date().timeIntervalSince(date) / 60)
        if minutes < 1 {
            return "刚刚"
        } else if minutes < 60 {
            return "\(minutes)分钟前"
        } else {
            let hours = minutes / 60
            return "\(hours)小时前"
        }
    }
}
```

---

## 4. 数据模型

### 4.1 Server → iOS 响应格式

```json
{
  "success": true,
  "data": {
    "device_id": "iphone-xxx",
    "pet_name": "小糖",
    "version": 42,
    "updated_at": "2025-10-31T10:30:00Z",
    "last_calculated_at": "2025-10-31T10:29:45Z",
    
    "values": {
      "energy": 75.0,
      "hunger": 40.0,
      "mood": 60.0
    },
    
    "state": {
      "current": "idle",
      "widget_quote": "今天好像有点无聊",
      "expression": {
        "pulse_rate": 95,
        "pulse_symbol": "●●●●●",
        "pulse_intensity": "极强",
        "color_hex": "#FFD700",
        "feeling": "傍晚渐近，但仍有充足的能量"
      }
    },
    
    "metadata": {
      "language": "zh",
      "next_push_at": "2025-10-31T11:45:00Z"
    },
    
    "engine_snapshot": {
      "rhythm": {
        "internal_phase": 0.15,
        "last_update": 1730368145.0
      },
      "energy": {
        "energy": 100.0
      }
    }
  },
  "timestamp": "2025-10-31T10:30:00Z"
}
```

### 4.2 iOS PetSnapshot 模型

```swift
struct PetSnapshot: Codable, Equatable, Identifiable {
    // 标识
    let id: String              // 等同于device_id
    let deviceId: String
    let petName: String
    
    // 版本控制
    let version: Int
    let updatedAt: Date
    let lastCalculatedAt: Date
    
    // 核心数值
    let energy: Double          // 0-100
    let hunger: Double          // 0-100
    let mood: Double            // 0-100
    
    // 状态
    let currentState: String    // sleep, hungry, play, idle, bored, grumpy, sleepy
    let widgetQuote: String
    
    // 表达（可选）
    let expression: Expression?
    
    // 元数据
    let language: String
    let nextPushAt: Date?
    
    struct Expression: Codable, Equatable {
        let pulseRate: Int
        let pulseSymbol: String
        let pulseIntensity: String
        let colorHex: String
        let feeling: String
    }
}
```

### 4.3 API 请求/响应模型

```python
# models.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class PetStateResponse(BaseModel):
    """宠物状态响应"""
    device_id: str
    pet_name: str
    version: int
    updated_at: datetime
    last_calculated_at: datetime
    
    values: Dict[str, float]  # energy, hunger, mood
    state: Dict[str, Any]     # current, widget_quote, expression
    metadata: Dict[str, Any]  # language, next_push_at
    engine_snapshot: Dict[str, Any]  # 内部状态快照

class InteractRequest(BaseModel):
    """互动请求"""
    device_id: str
    action: str  # feed, greet, play
    
class InteractResponse(BaseModel):
    """互动响应"""
    success: bool
    action: str
    data: PetStateResponse
    timestamp: datetime
```

---

## 5. 关键问题解答

### Q1: Widget怎么获取实时状态？

**A**: Widget不能"实时"，只能"准实时"

**机制**：
1. **App在前台时**：
   - App每30秒拉取Server → 写入App Group
   - Widget下次系统刷新时（≈15分钟）可见新状态

2. **App在后台/未运行时**：
   - 依赖iOS的Background Refresh（不保证频率）
   - Widget显示的是上次App活跃时的缓存

3. **用户体验**：
   - Widget显示"更新于X分钟前"
   - 点击Widget唤起App，App立即拉取最新状态

**示例场景**：
```
10:00 - 用户打开App，拉取到最新状态
10:00 - 用户喂食，状态更新到Server
10:01 - App写入App Group
10:15 - Widget系统刷新，显示10:01的状态
10:30 - Widget再次刷新（仍是10:01的状态，因为App未活跃）
10:45 - 用户再次打开App，拉取到10:45的最新状态
10:46 - Widget下次刷新时会看到10:45的状态
```

---

### Q2: 离线时怎么办？

**A**: 展示最后一次缓存 + 离线提示

**机制**：
```swift
func fetchFromServer() async {
    do {
        let state = try await api.getPetStatus(deviceId: deviceId)
        self.currentState = state
        self.isOffline = false
        appGroupStorage.save(state)
    } catch {
        // 网络错误，使用缓存
        if let cached = appGroupStorage.load() {
            self.currentState = cached
            self.isOffline = true  // 显示"离线"标识
        }
    }
}
```

**UI展示**：
- 顶部显示黄色横幅："离线模式，显示的是X分钟前的状态"
- 互动按钮变灰，点击提示"请连接网络"
- 重新联网后自动拉取最新状态

---

### Q3: Server冷启动延迟怎么处理？

**A**: 多层优化

**1. Vercel优化**：
- 使用Vercel的定时任务（Cron Jobs）每5分钟ping一次，保持函数warm
- 选择合适的Region（如果用户主要在中国，考虑香港节点）

**2. iOS超时处理**：
```swift
// 5秒超时
let state = try await api.getPetStatus(deviceId: deviceId)
    .timeout(seconds: 5)
    .fallback(to: cachedState)
```

**3. 加载体验**：
- 显示骨架屏或Loading动画
- 超时后自动切换到缓存
- 提示"加载中，请稍候"

---

### Q4: 多设备同步怎么办？

**A**: Server自动同步，无需iOS端处理

**场景示例**：
```
iPhone A                    Server (真源)                iPhone B
   │                             │                          │
   │  1. 喂食 (feed)              │                          │
   ├────────────────────────────>│                          │
   │  2. Server更新状态 v43       │                          │
   │     hunger: 40 → 20          │                          │
   │<────────────────────────────┤                          │
   │                             │                          │
   │                             │  3. 定期拉取 (30秒后)      │
   │                             │<─────────────────────────┤
   │                             │  4. 返回 v43 (hunger=20)  │
   │                             ├─────────────────────────>│
   │                             │                          │
```

**关键点**：
- ✅ Server维护唯一版本号
- ✅ 所有设备都从Server拉取最新状态
- ✅ 不需要复杂的冲突解决逻辑
- ✅ 后打开的设备会看到最新状态

---

### Q5: API调用频率会不会太高？

**A**: 需要权衡和优化

**当前设计**：
- App前台：每30秒拉取一次
- 互动时：立即调用一次
- Widget：系统控制（≈15分钟）

**日调用量估算**（单用户）：
- App活跃1小时/天：120次（每30秒）
- 互动：10次/天
- Widget刷新：96次/天（系统控制）
- **总计：≈200次/天/用户**

**Vercel限制**：
- Hobby计划：100GB-hours/月（约3300小时）
- Pro计划：1000GB-hours/月

**优化方案**：
1. 动态调整拉取频率（状态稳定时降低频率）
2. 使用WebSocket（未来考虑，但Widget不支持）
3. 批量请求（一次返回多个时间点的预测）

---

## 6. Server端实现

### 6.1 目录结构（更新：分层明确）

```
pet-life-server/
├── api/
│   └── index.py              # Vercel入口
├── src/
│   ├── models.py             # Pydantic模型
│   ├── kv_store.py           # Vercel KV封装（新增）
│   │
│   ├── life_adapter.py       # Life引擎适配器（改造）
│   │                         # 职责：调用micro-life-sim，协调各模块
│   │
│   ├── pet_state_mapper.py   # 宠物状态映射器（新增）
│   │                         # 职责：将Life原始数据映射为能量/饥饿/心情
│   │
│   ├── state_machine.py      # 宠物状态机（新增）
│   │                         # 职责：判断7种宠物状态
│   │
│   └── quote_generator.py    # 语录生成器（新增）
│                             # 职责：根据状态生成语录
├── main.py                   # 本地开发入口
├── requirements.txt
└── vercel.json
```

**关键变更**：
- ❌ 删除 `time_engine.py`（职责不清晰）
- ✅ 新增 `pet_state_mapper.py`（数值映射）
- ✅ 新增 `state_machine.py`（状态判断）
- ✅ 新增 `quote_generator.py`（语录生成）

### 6.2 核心改造点

#### 6.2.1 Vercel KV 持久化（新增）

```python
# src/kv_store.py

from vercel_kv import kv
import json
from typing import Optional, Dict
from datetime import datetime, timedelta

class PetStateStore:
    """宠物状态持久化"""
    
    TTL_DAYS = 30  # 30天无访问自动清理
    
    @staticmethod
    def get(device_id: str) -> Optional[Dict]:
        """获取状态"""
        key = f"pet:{device_id}"
        data = kv.get(key)
        
        if not data:
            return None
        
        return json.loads(data) if isinstance(data, str) else data
    
    @staticmethod
    def set(device_id: str, state: Dict):
        """保存状态"""
        key = f"pet:{device_id}"
        
        # 设置TTL（30天）
        ttl = int(timedelta(days=PetStateStore.TTL_DAYS).total_seconds())
        
        kv.set(key, json.dumps(state), ex=ttl)
    
    @staticmethod
    def create_initial_state(device_id: str) -> Dict:
        """创建初始状态"""
        return {
            'device_id': device_id,
            'pet_name': '小糖',
            'version': 1,
            'created_at': datetime.utcnow().isoformat(),
            'last_calculated_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            
            'values': {
                'energy': 100.0,
                'hunger': 50.0,
                'mood': 80.0
            },
            
            'state': {
                'current': 'idle',
                'widget_quote': '你好，我是小糖！'
            },
            
            'metadata': {
                'language': 'zh',
                'next_push_at': None
            },
            
            'engine_snapshot': {
                'rhythm': {
                    'internal_phase': 0.0,
                    'last_update': datetime.utcnow().timestamp()
                },
                'energy': {
                    'energy': 100.0
                }
            }
        }
```

#### 6.2.2 PetStateMapper - 数值映射器（新增）

```python
# src/pet_state_mapper.py

from typing import Dict

class PetStateMapper:
    """
    宠物状态映射器
    
    职责：将micro-life-sim的原始数据映射为宠物的三个数值
    - energy: 能量（直接映射）
    - hunger: 饥饿度（pet-life-server计算）
    - mood: 心情（综合能量和节律）
    """
    
    @staticmethod
    def map_from_life(life_raw_data: Dict) -> Dict:
        """
        从Life引擎的原始数据映射为宠物数值
        
        输入（来自micro-life-sim）：
        {
            'energy': 75.0,           # 生命能量 0-100
            'rhythm_phase': 0.35,     # 节律相位 0-1
        }
        
        输出（宠物数值）：
        {
            'energy': 75.0,           # 宠物精力
            'mood': 82.0,             # 心情值（综合计算）
        }
        
        注意：hunger需要单独计算（基于时间和喂食记录）
        """
        
        # 1. 能量直接映射
        energy = life_raw_data.get('energy', 100.0)
        
        # 2. 心情：综合能量和节律
        rhythm_phase = life_raw_data.get('rhythm_phase', 0.5)
        mood = PetStateMapper._calculate_mood(energy, rhythm_phase)
        
        return {
            'energy': energy,
            'mood': mood
        }
    
    @staticmethod
    def _calculate_mood(energy: float, rhythm_phase: float) -> float:
        """
        计算心情（pet-life-server的逻辑）
        
        规则：
        - 基础心情受能量影响（70%权重）
        - 节律影响：白天心情好，夜晚心情低
        - phase: 0.25-0.75 = 白天，其他 = 夜晚
        """
        
        # 基础心情（能量的70%）
        base_mood = energy * 0.7
        
        # 节律加成
        if 0.25 <= rhythm_phase <= 0.75:
            # 白天：心情好
            rhythm_bonus = 20
        else:
            # 夜晚：心情略低
            rhythm_bonus = -10
        
        # 合成心情，钳制在0-100
        mood = base_mood + rhythm_bonus
        mood = max(0, min(100, mood))
        
        return round(mood, 1)
    
    @staticmethod
    def calculate_hunger(current_hunger: float, minutes_elapsed: int, last_fed_minutes: int) -> float:
        """
        计算饥饿度（pet-life-server的逻辑）
        
        规则：
        - 每分钟增加 0.2
        - 钳制在 0-100
        
        参数：
        - current_hunger: 当前饥饿值
        - minutes_elapsed: 距离上次计算过去的分钟数
        - last_fed_minutes: 距离上次喂食过去的分钟数（未来用于更复杂逻辑）
        """
        
        # 简单线性增长
        hunger_increase = minutes_elapsed * 0.2
        new_hunger = current_hunger + hunger_increase
        
        # 钳制在0-100
        new_hunger = max(0, min(100, new_hunger))
        
        return round(new_hunger, 1)
```

---

#### 6.2.3 StateMachine - 状态机（新增）

```python
# src/state_machine.py

class PetStateMachine:
    """
    宠物状态机
    
    职责：根据能量/饥饿/心情判断7种宠物状态
    
    状态优先级（参考PRD）：
    1. 饥饿优先（生理需求）
    2. 能量优先（生理状态）
    3. 心情影响表现（心理状态）
    """
    
    # === 状态常量 ===
    SLEEP = 'sleep'
    SLEEPY = 'sleepy'
    HUNGRY = 'hungry'
    PLAY = 'play'
    IDLE = 'idle'
    BORED = 'bored'
    GRUMPY = 'grumpy'
    
    # === 阈值常量 ===
    ENERGY_LOW = 30
    ENERGY_MID = 50
    ENERGY_HIGH = 60
    
    HUNGER_HIGH = 70
    
    MOOD_LOW = 30
    MOOD_HIGH = 80
    
    @staticmethod
    def determine_state(energy: float, hunger: float, mood: float) -> str:
        """
        状态机判断逻辑
        
        参数：
        - energy: 0-100 (能量值)
        - hunger: 0-100 (饥饿值)
        - mood: 0-100 (心情值)
        
        返回：7种状态之一
        """
        
        # === 1. 饥饿优先（生理需求最重要）===
        if hunger >= PetStateMachine.HUNGER_HIGH:
            if energy < PetStateMachine.ENERGY_LOW:
                # 又饿又累，只能睡觉
                return PetStateMachine.SLEEP
            else:
                # 饿！
                return PetStateMachine.HUNGRY
        
        # === 2. 能量优先（生理状态）===
        if energy < PetStateMachine.ENERGY_LOW:
            # 太累了，必须睡觉
            return PetStateMachine.SLEEP
        
        if energy < PetStateMachine.ENERGY_MID:
            # 有点困
            return PetStateMachine.SLEEPY
        
        # === 3. 心情影响表现（心理状态）===
        if mood < PetStateMachine.MOOD_LOW:
            # 心情不好，闹脾气
            return PetStateMachine.GRUMPY
        
        if mood > PetStateMachine.MOOD_HIGH and energy > PetStateMachine.ENERGY_HIGH:
            # 开心且有精力，玩耍！
            return PetStateMachine.PLAY
        
        # === 4. 默认状态 ===
        if mood > 50:
            # 正常发呆/思考
            return PetStateMachine.IDLE
        else:
            # 有点无聊
            return PetStateMachine.BORED
```

---

#### 6.2.4 QuoteGenerator - 语录生成器（新增）

```python
# src/quote_generator.py

import random
from typing import Dict, List

class QuoteGenerator:
    """
    宠物语录生成器
    
    职责：根据状态生成宠物语录，支持多语言
    """
    
    # === 中文语录库 ===
    QUOTES_ZH: Dict[str, List[str]] = {
        'sleep': [
            '嘘…我在睡觉',
            'Zzz...',
            '别吵，让我再睡会儿'
        ],
        'sleepy': [
            '好困呀，要睡觉了',
            '打个哈欠~',
            '眼皮好重...'
        ],
        'hungry': [
            '我饿啦，给我吃的！',
            '肚子咕咕叫~',
            '饿得走不动了...'
        ],
        'play': [
            '嘿嘿，来玩吧！',
            '好开心啊！',
            '我们一起跳舞吧~'
        ],
        'idle': [
            '今天好像有点无聊',
            '在想些什么呢...',
            '发发呆~'
        ],
        'bored': [
            '好无聊啊',
            '陪我玩会儿嘛',
            '想做点什么...'
        ],
        'grumpy': [
            '哼，心情不好',
            '别理我',
            '不想说话'
        ]
    }
    
    # === 英文语录库 ===
    QUOTES_EN: Dict[str, List[str]] = {
        'sleep': [
            'Shh... I\'m sleeping',
            'Zzz...',
            'Don\'t wake me up'
        ],
        'sleepy': [
            'So sleepy...',
            '*yawn*',
            'Need to sleep soon'
        ],
        'hungry': [
            'I\'m hungry! Feed me!',
            'My tummy is rumbling~',
            'So hungry...'
        ],
        'play': [
            'Yay! Let\'s play!',
            'I\'m so happy!',
            'Let\'s dance together~'
        ],
        'idle': [
            'Feeling a bit bored today',
            'Thinking about something...',
            'Just chilling~'
        ],
        'bored': [
            'So bored',
            'Play with me please',
            'Want to do something...'
        ],
        'grumpy': [
            'Hmph, I\'m grumpy',
            'Leave me alone',
            'Don\'t want to talk'
        ]
    }
    
    @staticmethod
    def generate(state: str, language: str = 'zh') -> str:
        """
        根据状态生成语录
        
        参数：
        - state: 宠物状态 (sleep/sleepy/hungry/play/idle/bored/grumpy)
        - language: 语言 (zh/en)
        
        返回：随机选择的语录
        """
        
        if language == 'en':
            quotes = QuoteGenerator.QUOTES_EN.get(state, ['...'])
        else:
            # 默认中文
            quotes = QuoteGenerator.QUOTES_ZH.get(state, ['...'])
        
        return random.choice(quotes)
```

#### 6.2.5 LifeAdapter - 整合适配器（改造）

```python
# src/life_adapter.py

from datetime import datetime
from typing import Dict
import sys
import os

# 导入micro-life-sim（生命基础设施）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../micro-life-sim/src'))
from life import Life

# 导入pet-life-server自己的模块（产品逻辑）
from .kv_store import PetStateStore
from .pet_state_mapper import PetStateMapper
from .state_machine import PetStateMachine
from .quote_generator import QuoteGenerator


class LifeAdapter:
    """
    生命引擎适配器
    
    职责：
    1. 调用micro-life-sim获取原始数据（能量、节律）
    2. 使用pet-life-server的逻辑映射为宠物状态（能量/饥饿/心情→7种状态）
    3. 管理状态持久化（Vercel KV）
    4. 协调时间推进
    """
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.store = PetStateStore()
    
    def get_state(self) -> Dict:
        """获取当前宠物状态（自动推进时间）"""
        
        # 1. 从KV加载状态
        state = self.store.get(self.device_id)
        
        if not state:
            # 首次访问，创建初始状态
            state = self.store.create_initial_state(self.device_id)
            self.store.set(self.device_id, state)
            return self._format_response(state)
        
        # 2. 计算时间差
        now = datetime.utcnow()
        last_update = datetime.fromisoformat(state['last_calculated_at'])
        minutes_elapsed = int((now - last_update).total_seconds() / 60)
        
        # 3. 如果超过1分钟，推进时间
        if minutes_elapsed >= 1:
            state = self._advance_time(state, minutes_elapsed)
            self.store.set(self.device_id, state)
        
        return self._format_response(state)
    
    def _advance_time(self, state: Dict, minutes: int) -> Dict:
        """
        推进时间
        
        流程：
        1. 调用micro-life-sim推进底层引擎
        2. 用PetStateMapper映射数值
        3. 计算饥饿度
        4. 用StateMachine判断状态
        5. 用QuoteGenerator生成语录
        """
        
        # === Step 1: 调用micro-life-sim（生命基础设施）===
        life = Life()
        
        # TODO: 从snapshot恢复
        # life.restore_from_snapshot(state['engine_snapshot'])
        
        # 推进时间（分钟）
        for _ in range(minutes):
            life.tick()  # micro-life-sim的时间推进
        
        # 获取原始数据
        life_raw_data = {
            'energy': life.get_energy(),           # 假设Life有这个方法
            'rhythm_phase': life.get_rhythm_phase(),  # 假设Life有这个方法
        }
        
        # === Step 2: pet-life-server层的映射 ===
        
        # 2.1 映射能量和心情
        pet_values = PetStateMapper.map_from_life(life_raw_data)
        
        # 2.2 计算饥饿度（pet-life-server逻辑）
        pet_values['hunger'] = PetStateMapper.calculate_hunger(
            current_hunger=state['values'].get('hunger', 50.0),
            minutes_elapsed=minutes,
            last_fed_minutes=0  # TODO: 记录上次喂食时间
        )
        
        # 2.3 判断7种宠物状态（pet-life-server逻辑）
        current_state = PetStateMachine.determine_state(
            energy=pet_values['energy'],
            hunger=pet_values['hunger'],
            mood=pet_values['mood']
        )
        
        # 2.4 生成语录（pet-life-server逻辑）
        language = state.get('metadata', {}).get('language', 'zh')
        quote = QuoteGenerator.generate(current_state, language)
        
        # === Step 3: 更新状态 ===
        state['values'] = pet_values
        state['state']['current'] = current_state
        state['state']['widget_quote'] = quote
        state['last_calculated_at'] = datetime.utcnow().isoformat()
        state['updated_at'] = datetime.utcnow().isoformat()
        state['version'] += 1
        
        # 保存micro-life-sim的快照（供下次恢复）
        # state['engine_snapshot'] = life.to_snapshot()
        
        return state
    
    def interact(self, action: str) -> Dict:
        """
        处理用户互动
        
        Args:
            action: 互动类型 (feed/play/greet)
        """
        
        # 1. 先推进时间，获取最新状态
        state = self.store.get(self.device_id)
        if not state:
            state = self.store.create_initial_state(self.device_id)
        
        # 推进时间
        now = datetime.utcnow()
        last_update = datetime.fromisoformat(state['last_calculated_at'])
        minutes_elapsed = int((now - last_update).total_seconds() / 60)
        
        if minutes_elapsed >= 1:
            state = self._advance_time(state, minutes_elapsed)
        
        # 2. 应用互动效果
        if action == 'feed':
            state['values']['hunger'] = max(0, state['values']['hunger'] - 20)
            state['values']['mood'] = min(100, state['values']['mood'] + 10)
            # TODO: 记录last_fed_at
        
        elif action == 'play':
            state['values']['mood'] = min(100, state['values']['mood'] + 15)
            state['values']['energy'] = max(0, state['values']['energy'] - 10)
        
        elif action == 'greet':
            state['values']['mood'] = min(100, state['values']['mood'] + 5)
        
        # 3. 重新判断状态
        current_state = PetStateMachine.determine_state(
            energy=state['values']['energy'],
            hunger=state['values']['hunger'],
            mood=state['values']['mood']
        )
        
        # 4. 生成互动语录
        language = state.get('metadata', {}).get('language', 'zh')
        quote = self._get_interaction_quote(action, language)
        
        state['state']['current'] = current_state
        state['state']['widget_quote'] = quote
        
        # 5. 更新版本和时间
        state['version'] += 1
        state['updated_at'] = datetime.utcnow().isoformat()
        state['last_calculated_at'] = datetime.utcnow().isoformat()
        
        # 6. 保存到KV
        self.store.set(self.device_id, state)
        
        return self._format_response(state)
    
    def _get_interaction_quote(self, action: str, language: str) -> str:
        """获取互动语录"""
        quotes = {
            'feed': {
                'zh': '好吃！谢谢你~',
                'en': 'Yummy! Thank you~'
            },
            'play': {
                'zh': '好开心啊！',
                'en': 'So happy!'
            },
            'greet': {
                'zh': '嗨！见到你真好~',
                'en': 'Hi! Nice to see you~'
            }
        }
        
        return quotes.get(action, {}).get(language, '...')
    
    def reset(self) -> Dict:
        """重置状态（调试用）"""
        state = self.store.create_initial_state(self.device_id)
        self.store.set(self.device_id, state)
        return self._format_response(state)
    
    def _format_response(self, state: Dict) -> Dict:
        """格式化响应"""
        return {
            'device_id': state['device_id'],
            'pet_name': state['pet_name'],
            'version': state['version'],
            'updated_at': state['updated_at'],
            'last_calculated_at': state['last_calculated_at'],
            'values': state['values'],
            'state': state['state'],
            'metadata': state.get('metadata', {}),
            'engine_snapshot': state.get('engine_snapshot', {})
        }
```

#### 6.2.4 API 端点更新

```python
# api/index.py 或 main.py

@app.get("/api/pet/status")
async def get_pet_status(device_id: str):
    """获取宠物状态（自动推进时间）"""
    try:
        if not device_id:
            raise HTTPException(status_code=400, detail="device_id is required")
        
        adapter = LifeAdapter(device_id)
        state = adapter.get_state()
        
        return {
            "success": True,
            "data": state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 7. iOS端实现

### 7.1 核心组件

#### 7.1.1 PetStateManager（状态管理）

```swift
// Core/StateManagement/PetStateManager.swift

import Foundation
import Combine

@MainActor
class PetStateManager: ObservableObject {
    // MARK: - Published State
    
    @Published var currentState: PetSnapshot?
    @Published var isLoading: Bool = false
    @Published var isOffline: Bool = false
    @Published var lastError: Error?
    
    // MARK: - Dependencies
    
    private let apiClient: PetAPIClient
    private let appGroupStorage: AppGroupStorage
    private let deviceId: String
    
    // MARK: - Polling
    
    private var pollingTimer: Timer?
    private let pollingInterval: TimeInterval = 30  // 30秒
    
    // MARK: - Initialization
    
    init(
        apiClient: PetAPIClient = .shared,
        appGroupStorage: AppGroupStorage = .shared,
        deviceId: String = DeviceID.current
    ) {
        self.apiClient = apiClient
        self.appGroupStorage = appGroupStorage
        self.deviceId = deviceId
        
        // 启动时加载缓存
        self.currentState = appGroupStorage.load()
    }
    
    // MARK: - Public Methods
    
    func startPolling() {
        // 立即拉取一次
        Task {
            await fetchFromServer()
        }
        
        // 定时拉取
        pollingTimer = Timer.scheduledTimer(
            withTimeInterval: pollingInterval,
            repeats: true
        ) { [weak self] _ in
            Task {
                await self?.fetchFromServer()
            }
        }
    }
    
    func stopPolling() {
        pollingTimer?.invalidate()
        pollingTimer = nil
    }
    
    func fetchFromServer() async {
        isLoading = true
        lastError = nil
        
        do {
            let state = try await apiClient.getPetStatus(deviceId: deviceId)
            
            self.currentState = state
            self.isOffline = false
            
            // 保存到App Group
            appGroupStorage.save(state)
            
        } catch {
            print("Failed to fetch: \(error)")
            lastError = error
            
            // 使用缓存
            if currentState == nil {
                currentState = appGroupStorage.load()
            }
            isOffline = true
        }
        
        isLoading = false
    }
    
    func interact(action: String) async {
        guard var state = currentState else { return }
        
        // 乐观更新
        state = optimisticUpdate(state: state, action: action)
        self.currentState = state
        appGroupStorage.save(state)
        
        // 异步调用Server
        do {
            let newState = try await apiClient.interact(deviceId: deviceId, action: action)
            
            // 以Server为准
            self.currentState = newState
            self.isOffline = false
            appGroupStorage.save(newState)
            
        } catch {
            print("Interact failed: \(error)")
            lastError = error
            // 保留乐观更新，下次拉取会被覆盖
        }
    }
    
    // MARK: - Private
    
    private func optimisticUpdate(state: PetSnapshot, action: String) -> PetSnapshot {
        var newState = state
        
        switch action {
        case "feed":
            newState.hunger = max(0, state.hunger - 20)
            newState.mood = min(100, state.mood + 10)
            newState.widgetQuote = "好吃！谢谢你~"
            
        case "play":
            newState.mood = min(100, state.mood + 15)
            newState.energy = max(0, state.energy - 10)
            newState.widgetQuote = "好开心啊！"
            
        case "greet":
            newState.mood = min(100, state.mood + 5)
            newState.widgetQuote = "嗨！见到你真好~"
            
        default:
            break
        }
        
        newState.version += 1
        newState.updatedAt = Date()
        
        return newState
    }
}
```

#### 7.1.2 AppGroupStorage（共享存储）

```swift
// Core/Persistence/AppGroupStorage.swift

import Foundation

class AppGroupStorage {
    static let shared = AppGroupStorage()
    
    private let appGroupID = "group.com.xiaotang.pet"
    private let stateKey = "pet_state"
    
    private var userDefaults: UserDefaults? {
        UserDefaults(suiteName: appGroupID)
    }
    
    func save(_ state: PetSnapshot) {
        guard let data = try? JSONEncoder().encode(state) else {
            print("Failed to encode state")
            return
        }
        
        userDefaults?.set(data, forKey: stateKey)
    }
    
    func load() -> PetSnapshot? {
        guard let data = userDefaults?.data(forKey: stateKey),
              let state = try? JSONDecoder().decode(PetSnapshot.self, from: data) else {
            return nil
        }
        
        return state
    }
    
    func clear() {
        userDefaults?.removeObject(forKey: stateKey)
    }
}
```

---

## 8. 潜在风险

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解方案 | 优先级 |
|------|------|------|----------|--------|
| **Widget刷新延迟** | 用户看到过时状态 | 高 | 显示"更新于X分钟前"提示 | P0 |
| **Server冷启动** | 首次请求慢 | 中 | Cron保持warm + 超时降级 | P1 |
| **网络不稳定** | 离线体验差 | 中 | 本地缓存 + 离线提示 | P0 |
| **API调用成本** | 超出Vercel免费额度 | 低 | 监控用量 + 动态调频 | P2 |
| **Vercel KV限制** | 存储容量不足 | 低 | 30天TTL + 监控 | P2 |
| **状态不一致** | 多端数据冲突 | 低 | Server为真源，自动同步 | P1 |

### 8.2 产品风险

| 风险 | 影响 | 缓解方案 |
|------|------|----------|
| **Widget不够实时** | 用户体验不佳 | 教育用户"Widget是概览，App是交互" |
| **离线无法互动** | 功能受限 | 明确提示"需要网络连接" |
| **Server故障** | 服务不可用 | 监控告警 + 降级到缓存 |

---

## 9. 待讨论事项

### 9.1 高优先级

- [ ] **App拉取频率**：30秒合适吗？还是改为60秒？
  - 考虑因素：实时性 vs 电量消耗 vs API成本

- [ ] **Widget延迟可接受度**：15分钟延迟，产品上能接受吗？
  - 替代方案：显著的"更新时间"提示

- [ ] **离线体验**：只显示缓存+提示，还是需要本地降级逻辑？

- [ ] **Vercel KV配置**：
  - 需要申请Vercel Pro计划吗？
  - KV额度够用吗？（Hobby: 256MB，Pro: 512GB）

### 9.2 中优先级

- [ ] **micro-life-sim集成**：
  - 需要实现`Life.from_snapshot()`和`Life.advance_minutes()`吗？
  - 还是先用简化版时间推进？

- [ ] **语录生成**：
  - Server生成还是iOS本地生成？
  - 需要接入AI吗？

- [ ] **推送通知**：
  - Server端触发推送（通过APNs）？
  - 还是iOS本地调度？

### 9.3 低优先级

- [ ] **性能监控**：需要接入APM工具吗？（如Sentry）
- [ ] **A/B测试**：拉取频率需要做实验吗？
- [ ] **国际化**：Server需要支持多语言吗？

---

## 10. 下一步行动

### 10.1 需要确认的决策

1. **Widget延迟的可接受性**（影响整体架构）
2. **App拉取频率**（30秒 vs 60秒 vs 动态调整）
3. **Vercel KV方案确认**（配置、额度、成本）
4. **micro-life-sim集成深度**（完整集成 vs 简化版）

### 10.2 技术准备

- [ ] Vercel KV环境配置
- [ ] iOS App Group设置
- [ ] API接口联调测试
- [ ] 性能基准测试

---

## 附录

### A. 参考文档

- [Vercel KV文档](https://vercel.com/docs/storage/vercel-kv)
- [iOS App Groups](https://developer.apple.com/documentation/xcode/configuring-app-groups)
- [WidgetKit Best Practices](https://developer.apple.com/documentation/widgetkit)
- [micro-life-sim项目](https://github.com/DeeWooo/micro-life-sim)

### B. 修订历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| 0.1 | 2025-10-31 | Ivy & AI | 初始草案，Server为真源架构设计 |
| 0.2 | 2025-10-31 | Ivy & AI | **重大调整**：明确职责边界，micro-life-sim只负责生命基础设施，宠物状态逻辑由pet-life-server负责。新增PetStateMapper、StateMachine、QuoteGenerator三个模块。 |

---

**文档结束**

