# Vue + TypeScript 前端功能扩展通用准则

> **定位**：本文件定义 Vue 3 + TypeScript 前端项目新增业务模块、新页面、新组件、新状态、新 API、新交互能力时的通用扩展规则。
>
> 本文件是可复用于其他 Vue + TypeScript 项目的工程基线，不绑定当前项目的具体业务。项目级 `DEVELOPMENT.md` 可以补充实际目录、组件库、构建命令和部署约束，但不应改变本文件定义的职责边界。

---

## 1. 扩展总原则

新增功能不是“增加几个页面和接口调用”，而是一次完整的 Feature 扩展。

标准流程：

```text
需求
 ↓
业务边界
 ↓
Feature 归属
 ↓
UX / UI / Interaction Contract
 ↓
Backend API Contract
 ↓
Types / API Client
 ↓
State / Composable
 ↓
Components / Views
 ↓
Permission / Error / Loading / Empty
 ↓
Accessibility / Responsive
 ↓
Unit / Component / Integration / E2E
 ↓
Documentation
 ↓
Type Check / Lint / Build
 ↓
Review
```

核心原则：

1. 优先扩展已有 Feature，不因一个页面随意创建新顶层模块。
2. 新业务必须有明确边界，不把业务代码堆进 `components/`、`views/`、`stores/` 或 `utils/`。
3. API Contract、类型、权限、错误和状态必须一起设计。
4. UI 只是表现层，不能成为业务规则的唯一载体。
5. 新功能必须考虑桌面、窄屏、键盘操作、异常状态和空状态，而不是只实现成功路径。

---

## 2. Feature 归属判断

新增功能首先判断属于：

```text
现有 Feature 的扩展
        │
        ├── 是 → 扩展现有 Feature
        │
        └── 否 → 新建 Feature
```

新 Feature 至少应该能够独立说明：

```text
业务目标
用户角色
页面 / View
API
状态
组件
权限
依赖的其他 Feature
```

推荐结构：

```text
features/
└── <domain>/
    ├── api/
    ├── components/
    ├── composables/
    ├── stores/
    ├── types/
    ├── views/
    ├── constants/       # 仅 Feature 私有常量
    ├── utils/           # 仅 Feature 私有、无业务副作用工具
    └── index.ts
```

并非每个 Feature 都必须创建所有目录；**按实际需要创建，禁止模板化制造空目录**。

---

## 3. 新页面扩展

新增页面推荐：

```text
features/<domain>/views/
```

View 负责：

```text
页面布局
Feature 组件组合
路由参数接入
页面级状态展示
页面级交互编排
```

View 不负责：

```text
复杂 API 实现
复杂业务规则
底层 HTTP Client
跨模块状态修改
权限安全判断
大型数据转换
```

页面应明确：

```text
Loading
Success
Empty
Error
Permission Denied
```

列表页还应考虑：

```text
Pagination
Filtering
Sorting
Search
Refresh
Stale Data
Partial Failure
```

---

## 4. 新组件扩展

组件新增前必须先判断复用层级：

```text
业务专属
   ↓
Feature Component

多个 Feature 共享但仍有业务语义
   ↓
Shared / Domain Component

完全无业务语义
   ↓
Global UI Component / Design System
```

禁止因为“以后可能复用”就过早把组件提升为全局组件。

组件提升到共享层必须满足：

```text
至少两个稳定使用场景
API 边界清晰
无单一 Feature 私有状态
无隐式业务依赖
```

---

## 5. API 扩展

新增 API 必须先确认 Backend Contract：

```text
Backend OpenAPI / Contract
          ↓
Frontend DTO Types
          ↓
API Client
          ↓
Feature API
          ↓
Composable / Store
          ↓
View
```

禁止：

```text
View → axios/fetch → URL + any
```

每个 Feature 的 API 方法应保持资源和业务边界清晰，例如：

```text
features/orders/api/
├── orders.api.ts
└── orders.types.ts
```

如果采用自动生成类型或 Client，生成代码与手写业务代码必须分离。

---

## 6. API Contract 变更

Backend Contract 发生变化时，必须评估：

```text
Request
Response
Error Code
Pagination
Enum
Nullable
Optional
Authentication
Authorization
```

对于 Breaking Change：

```text
Backend v2
 ↓
Frontend compatibility layer / migration
 ↓
Feature migration
 ↓
旧 Contract 移除
```

禁止在页面中同时散落维护多个版本的 DTO。

---

## 7. State 扩展规则

新增状态前必须回答：

```text
这个状态是谁拥有？
生命周期多长？
是否需要跨页面？
是否来自服务器？
是否需要持久化？
是否可以重新获取？
```

优先级：

```text
组件状态
 ↓
Composable 状态
 ↓
Feature Store
 ↓
全局 Store
```

能在组件内解决的问题，不进入 Store。

能在 Feature 内解决的问题，不进入全局 Store。

服务器状态不要机械复制为多个 Pinia 状态源。

---

## 8. Composable 扩展

新增 composable 必须表达一个明确能力：

```text
useOrderList()
useOrderForm()
useWorkflowPolling()
usePermission()
```

而不是：

```text
useCommon()
useHelper()
useBusiness()
```

异步 composable 必须处理：

```text
loading
error
success
cancellation
stale response
unmount cleanup
retry
```

具有副作用的 composable 必须明确何时创建、何时清理。

---

## 9. Store 扩展

新增 Store 前必须证明它确实需要跨组件 / 跨页面共享。

Store 应包含：

```text
State
Getters / Derived State
Actions
必要的持久化策略
```

Store 不应包含：

```text
页面模板逻辑
大量 DOM 操作
组件生命周期细节
无限制 API 聚合
所有 Feature 的公共状态
```

禁止形成：

```text
God Store
```

如果一个 Store 同时管理多个无关业务领域，应重新评估边界。

---

## 10. 新业务规则

业务规则应优先放在：

```text
Feature Composable
Feature Domain / Service
可测试纯函数
```

而不是：

```text
Template
watch 链
Router Guard
Store 中的隐式副作用
```

复杂状态机优先显式建模：

```text
State
Event
Transition
Guard
Action
```

不要使用大量布尔字段表达互斥状态：

```ts
isLoading
isSubmitting
isFinished
isFailed
isCancelled
```

如果这些状态互斥，应考虑 Discriminated Union 或显式状态模型。

---

## 11. 表单功能扩展

新表单至少定义：

```text
Initial State
Field Types
UI Validation
Submit State
Server Validation
Success
Error
Cancel / Reset
Dirty State
```

提交过程必须防止重复提交：

```text
idle
 ↓
submitting
 ↓
success / error
```

前端校验只负责用户体验，后端校验仍是最终安全与业务边界。

---

## 12. 权限扩展

新增页面、菜单、按钮或操作必须明确权限模型：

```text
Route Permission
Page Permission
Action Permission
Resource Scope
Tenant Scope
```

前端权限用于：

```text
显示 / 隐藏
禁用
导航
用户提示
```

不能依赖前端隐藏按钮实现安全控制。

真实授权必须由 Backend Enforcement 完成。

---

## 13. 多租户扩展

涉及租户的数据展示和操作必须明确：

```text
Current Tenant
Tenant Switch
Resource Scope
Permission Scope
Cache Key Scope
```

禁止仅依赖前端传入的 `tenantId` 判断用户是否有权访问该租户。

缓存和本地持久化数据也必须防止跨租户污染。

---

## 14. Loading / Empty / Error 状态扩展

新增异步功能必须同时设计状态模型：

```text
idle
loading
success
empty
error
```

复杂业务可以增加：

```text
refreshing
saving
retrying
partial
stale
conflict
permission-denied
```

避免：

```text
loading = false
```

作为所有异步状态的唯一表达方式。

---

## 15. 并发与竞态

新增搜索、分页、实时刷新、轮询、详情切换等功能时必须评估竞态：

```text
Request A
Request B
 ↓
B 先返回
 ↓
A 后返回
 ↓
A 不得覆盖 B
```

根据场景选择：

```text
AbortController
Request Sequence
Latest-only semantics
Debounce / Throttle
Cache Deduplication
```

轮询必须支持停止、组件卸载清理和失败退避。

---

## 16. 实时 / WebSocket / SSE 扩展

新增实时能力必须明确：

```text
Connection Lifecycle
Authentication
Reconnect
Backoff
Heartbeat
Message Schema
Ordering
Duplicate Handling
Disconnect Cleanup
```

禁止在组件中直接实现完整 WebSocket 生命周期管理。

推荐：

```text
Transport Client
 ↓
Feature Event Handler
 ↓
State Update
 ↓
UI
```

---

## 17. 文件上传 / 下载

涉及文件功能必须考虑：

```text
File Type
Size Limit
Progress
Cancellation
Retry
Resume（需要时）
Server Validation
Download Permission
Filename Safety
```

不要把大文件直接转换成大量 Base64 放入 Store。

敏感下载必须使用后端授权机制，不能把可长期访问的敏感 URL 暴露给用户。

---

## 18. 表格 / 大数据量页面

新增大型列表必须先评估：

```text
Pagination
Server-side Filtering
Server-side Sorting
Virtualization
Incremental Loading
Column Configuration
Export
```

禁止一次性加载不受控的大量数据并全部交给浏览器渲染。

导出大量数据优先采用异步任务模式：

```text
Create Export Task
 ↓
Backend Processing
 ↓
Progress / Status
 ↓
Download
```

---

## 19. Design System 扩展

新增 UI 组件应优先复用已有：

```text
Design Tokens
Base Components
Patterns
```

新建组件前检查：

```text
是否已有等价组件？
是否只是样式变体？
是否应该扩展 Variant？
是否真的需要新组件？
```

禁止同一项目出现多个语义相同但 API 不兼容的 Button、Dialog、Table、Form 等基础组件。

---

## 20. 响应式设计

新增页面必须定义主要断点和降级行为：

```text
Desktop
Tablet
Mobile / Narrow viewport
```

不是简单地让所有内容“自动缩小”。

复杂表格、侧栏、工具栏等需要定义：

```text
隐藏
折叠
横向滚动
重新布局
分页 / 分组
```

---

## 21. Accessibility 扩展

新增交互组件必须检查：

```text
Keyboard
Focus
Focus Trap
Semantic HTML
ARIA
Screen Reader
Error Announcement
```

Dialog、Drawer、Dropdown、Menu、Tooltip 等组件尤其需要明确焦点生命周期。

任何关键操作不能只依赖颜色、图标或 hover 表达。

---

## 22. 国际化扩展

如果项目支持 i18n，新功能禁止直接硬编码用户可见文本。

应使用：

```text
Feature Translation Namespace
 ↓
Locale Resources
 ↓
Typed Translation Key（如果项目支持）
```

同时考虑：

```text
Pluralization
Date / Time
Number
Currency
Long Text
RTL（需要时）
```

不要在通用 locale 文件中无限堆积所有 Feature 文案。

---

## 23. 前端缓存

新增缓存功能必须明确：

```text
Cache Key
Scope
TTL
Invalidation
Version
Tenant Boundary
Permission Boundary
```

写操作后必须明确哪些缓存需要失效或重新验证。

禁止无期限缓存业务数据。

---

## 24. 错误与可观测性

新功能至少应能定位：

```text
Feature
Operation
Request ID / Trace ID
Backend Error Code
Client Error
```

生产环境日志禁止包含：

```text
Token
Secret
密码
完整敏感业务数据
```

错误展示应面向用户，诊断信息应面向开发和运维，两者分离。

---

## 25. 测试扩展矩阵

| 新增内容 | 最低测试建议 |
|---|---|
| Pure Function | Unit |
| Composable | Unit |
| Component | Component |
| Form | Component + Integration |
| API Client | Unit / Integration |
| Store | Unit |
| Router / Permission | Integration |
| Feature Page | Component + Integration |
| Critical User Journey | E2E |
| WebSocket / SSE | Integration |
| File Upload | Integration + E2E（关键流程） |

测试重点是**行为和边界**，而不是为了覆盖率机械增加断言。

---

## 26. Mock 与 Contract 验证

Mock 必须与真实 Backend Contract 保持一致。

新增 API 后：

```text
Contract
 ↓
Mock / Fixture
 ↓
Integration
```

重要接口必须至少存在一层真实 Contract 或 Integration 验证。

禁止长期维护“为了让测试通过”而与生产接口不同的 Mock 数据结构。

---

## 27. 性能检查清单

新增大型 Feature 前至少评估：

```text
Bundle Size
Initial Load
Chunk Size
Network Requests
API Payload
Rendering Cost
Reactive Dependencies
Memory
Long Task
```

性能优化必须说明：

```text
问题指标
优化方案
验证方式
优化结果
```

---

## 28. 安全检查清单

新增功能必须检查：

```text
XSS
CSRF
Token Exposure
Sensitive URL
File Upload
Open Redirect
Third-party Content
Permission Bypass
Tenant Isolation
Dependency Risk
```

尤其禁止：

```text
v-html + untrusted content
localStorage 保存高敏感凭据（除非安全架构明确要求）
把权限结果当作后端授权
把 Secret 放进 VITE_* 等公开构建变量
```

前端构建变量默认视为可能暴露给用户。

---

## 29. 依赖新增准则

新增 npm 依赖前必须确认：

```text
现有依赖是否已经提供能力？
包是否仍然维护？
Bundle Size？
License？
Security Risk？
Tree-shaking？
TypeScript Support？
```

不要为了一个很小的工具函数引入重量级依赖。

新增 UI / State / HTTP / Utility 框架级依赖必须评估对现有架构的影响。

---

## 30. Breaking Change 规则

以下变化默认视为潜在 Breaking Change：

```text
公共组件 Props 删除 / 重命名
Emit payload 改变
Store State / Action 改变
Route 改变
API Contract 改变
权限模型改变
全局 CSS Token 改变
公共 Composable API 改变
```

必须评估调用方，并优先提供迁移路径，而不是直接修改后让所有消费者自行修复。

---

## 31. Feature 对外暴露

Feature 应通过明确入口暴露能力：

```text
features/<domain>/index.ts
```

避免其他 Feature 深度访问内部文件：

```text
❌ features/order/components/internal/xxx
❌ features/order/stores/privateStore
```

推荐：

```text
Feature A
 ↓
Feature B public API
```

而不是：

```text
Feature A
 ↓
Feature B internal implementation
```

这有助于后续重构和拆分。

---

## 32. Feature 间依赖

依赖必须尽量单向：

```text
Feature A
   ↓
Feature B
```

避免：

```text
Feature A ↔ Feature B
```

如果两个 Feature 形成循环依赖，应考虑：

```text
提取 Shared Contract
提取 Shared UI Pattern
调整业务边界
通过事件 / command 解耦
```

禁止通过全局 Store 偷渡依赖来掩盖循环依赖。

---

## 33. 删除与废弃

功能删除同样必须完整处理：

```text
Route
Menu
Component
Composable
Store
API Client
Types
Translations
Tests
Documentation
Dependencies
```

禁止只删除页面而留下大量 dead code。

废弃 API / Component 必须标记迁移策略和最终删除条件。

---

## 34. 新 Feature Definition of Done

一个 Feature 只有满足以下条件才视为完成：

```text
[ ] 业务边界明确
[ ] Feature 归属明确
[ ] API Contract 明确
[ ] TypeScript 类型完整
[ ] API Client 完成
[ ] State 边界明确
[ ] Components / Views 完成
[ ] Loading / Empty / Error 完成
[ ] Permission 完成
[ ] Accessibility 检查
[ ] Responsive 检查
[ ] Error / Observability 完成
[ ] Unit / Component Test 完成
[ ] Integration Test（适用时）
[ ] E2E（关键路径）
[ ] Type Check
[ ] Lint
[ ] Production Build
[ ] 文档更新
[ ] 无无主 dead code
[ ] Code Review
```

---

## 35. 通用扩展决策表

| 场景 | 首选位置 | 原则 |
|---|---|---|
| 新业务 | `features/<domain>` | Feature First |
| 新页面 | Feature `views/` | 页面编排 |
| Feature 组件 | Feature `components/` | 业务 UI |
| 跨 Feature UI | `components/` | 无业务耦合 |
| Feature Composable | Feature `composables/` | 能力内聚 |
| 跨 Feature Composable | `composables/` | 稳定公共能力 |
| Feature Store | Feature `stores/` | 最小共享范围 |
| 全局 Store | `stores/` | 真正全局状态 |
| Feature 类型 | Feature `types/` | 就近维护 |
| 全局技术类型 | `types/` | 不放业务类型 |
| Feature API | Feature `api/` | Contract 驱动 |
| HTTP Client | `services/` | 技术能力 |
| 纯工具 | `utils/` | 无业务语义 |
| 全局样式 / Token | `styles/` | Design System |

---

## 36. 最终扩展原则

新增功能时始终遵循：

```text
先判断边界
    ↓
再确定归属
    ↓
再定义 Contract
    ↓
再实现 UI / State / API
    ↓
再补齐 Error / Permission / Accessibility
    ↓
再测试
    ↓
再文档化
```

不要：

```text
先建页面
 ↓
页面里写 API
 ↓
页面里写业务规则
 ↓
全部塞 Pinia
 ↓
最后再补权限和测试
```

**前端架构的目标不是目录看起来复杂，而是让每一个 Feature 都能够独立理解、独立测试、独立演进，并且能够在未来被重构、拆分或替换而不牵一发动全身。**
