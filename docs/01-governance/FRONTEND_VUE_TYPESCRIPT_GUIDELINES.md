# Vue + TypeScript 前端通用项目开发准则

> **定位**：本文件定义 Vue 3 + TypeScript 企业级前端项目的通用工程基线，并以当前项目已经采用的 `frontend/src/api`、`router`、`utils`、`views` 等目录作为落地参考。
>
> **重要原则**：本准则是通用规范，不要求所有项目立即迁移为某一种 Feature First 目录。对于已有项目，应**保留既有目录架构、职责和稳定 API**，通过新增功能逐步收敛边界；只有业务规模和依赖复杂度达到拆分条件时，才引入 `features/<domain>` 等更细粒度结构。
>
> 本文件遵循 `UNIVERSAL_DEVELOPMENT_GUIDELINES.md`。项目级 `DEVELOPMENT.md` 可以补充具体 UI 组件库、目录实例、命令、CI/CD 和部署环境，但不得无故违反本文件的核心工程原则。

---

## 1. 核心原则

1. **Contract First**：前端 API 类型以正式 Backend Contract 为准，优先从 OpenAPI 等契约生成或同步类型。
2. **Incremental Architecture**：基于现有目录持续演进，不因架构规范而进行无收益的大规模目录迁移。
3. **Feature Boundary**：新增业务必须有清晰边界；规模较小时可落在现有 `api/views/utils`，规模增长后再按 Feature 聚合。
4. **State Boundary**：区分组件状态、页面状态、业务共享状态、服务端状态和持久化状态。
5. **UI / Business Separation**：View 和 Component 负责展示与交互编排，业务规则进入可测试的 composable / service / domain logic。
6. **Type First**：TypeScript 使用严格类型；禁止通过 `any`、`as any` 或 `@ts-ignore` 长期绕过类型系统。
7. **Security Boundary**：前端权限控制只负责 UX；真正授权、租户隔离和资源访问必须由后端执行。
8. **Observable UI**：异步操作必须具备 Loading / Success / Empty / Error 等可观测状态。
9. **Accessible by Default**：新交互默认支持键盘、焦点、语义化 HTML 和辅助技术。
10. **Measured Performance**：性能优化必须有问题、指标、方案和验证结果。
11. **Testable Delivery**：测试按照 Unit / Component / Integration / E2E 的风险和边界分层。
12. **Small and Traceable Changes**：一个提交尽量对应一个可解释的工程变化。

---

## 2. 推荐技术基线

```text
Vue 3
TypeScript strict mode
Vite
Vue Router
Pinia（按需）
Vue Test Utils
Vitest
Playwright
ESLint
Prettier
```

具体项目可以替换实现，但必须提供等价能力：

```text
类型检查
代码规范
单元/组件测试
关键浏览器流程测试
生产构建验证
```

依赖选型必须服从现有项目，而不是为了“标准化”强制引入新框架。

---

## 3. 基于当前项目的目录基线

当前项目采用的前端基础目录为：

```text
frontend/
├── docs/
├── scripts/
├── tests/
├── src/
│   ├── api/               # 后端 API / Contract 接入层
│   ├── router/            # 路由与导航入口
│   ├── utils/             # 无业务语义的纯工具
│   ├── views/             # 页面级 View
│   ├── App.vue
│   ├── main.ts
│   └── env.d.ts
├── package.json
├── vite.config.ts
├── vitest.config.ts
└── playwright.config.ts
```

这是**当前项目基线**，不是要求所有项目必须完全复制的模板。

随着项目增长，可以在不破坏既有目录职责的前提下逐步增加：

```text
src/
├── components/            # 跨业务复用 UI
├── composables/           # 跨业务通用能力
├── stores/                # 真正全局客户端状态
├── layouts/               # 页面布局
├── services/              # 跨 Feature 技术服务
├── types/                 # 全局技术类型
├── styles/                # 全局样式 / Design Tokens
└── features/              # 业务规模达到条件后按领域聚合
    └── <domain>/
```

**禁止为了“完整目录”预先创建大量空目录。**

---

## 4. 目录职责边界

### `api/`

负责：

```text
HTTP API Client
Request / Response DTO
Contract Adapter
```

不负责：

```text
页面状态
DOM
完整业务流程
```

### `router/`

负责：

```text
Route Definition
Navigation Guard
Route Metadata
```

不负责完整业务流程。

### `views/`

负责：

```text
页面布局
页面级数据编排
Feature Component 组合
页面交互
```

复杂业务规则不得长期堆积在 View。

### `utils/`

只允许：

```text
纯函数
无业务语义
低副作用
可独立测试
```

禁止将业务 Service、API Client、Store、权限逻辑塞进 `utils/`。

### `components/`

仅放真正跨业务复用的 UI 组件。

业务专属组件优先放在对应 Feature 或页面邻近位置。

### `composables/`

放跨页面 / 跨 Feature 的稳定组合式能力。

业务专属 composable 应优先就近放置在 Feature 内。

### `stores/`

仅放真正跨页面、跨 Feature 的客户端状态。

### `services/`

放跨业务的技术服务或稳定基础能力，例如：

```text
HTTP Client
Download Client
Upload Client
WebSocket Transport
Storage Adapter
```

业务 Service 不应无边界集中在这里。

### `features/`

不是当前项目必须立即迁移的目录，而是**业务复杂度增长后的扩展机制**。

推荐：

```text
features/<domain>/
├── api/
├── components/
├── composables/
├── stores/
├── types/
├── views/
└── index.ts
```

---

## 5. 现有项目向 Feature 演进规则

不要进行一次性“大搬家”。推荐：

```text
当前：
api/ + views/ + utils/
        ↓
业务数量增长
        ↓
按领域识别耦合边界
        ↓
新增业务优先就近组织
        ↓
必要时引入 features/<domain>
        ↓
逐步迁移
```

只有出现以下情况之一，才建议引入 Feature 聚合：

```text
同一业务散落超过多个目录
页面 / API / Store / Component 强耦合
多个开发者频繁修改同一业务区域
业务测试难以定位
Feature 需要独立演进
```

迁移时必须保持：

```text
Route 不无故改变
API Contract 不无故改变
用户行为不无故改变
测试结果不下降
旧代码最终删除
```

---

## 6. 新功能标准扩展流程

任何新业务功能必须遵循：

```text
需求
 ↓
业务边界
 ↓
检查已有 API / View / Component / Utils
 ↓
确认 Backend Contract
 ↓
确定代码归属
 ↓
Type / DTO
 ↓
API
 ↓
State / Composable
 ↓
Component / View
 ↓
Permission
 ↓
Loading / Empty / Error
 ↓
Accessibility / Responsive
 ↓
Test
 ↓
Type Check / Lint / Build
 ↓
Documentation
```

**先复用、后扩展；先判断边界、再创建目录。**

---

## 7. Feature 归属决策

新增代码优先按照以下顺序判断：

```text
已有业务 Feature？
    ↓ 是
扩展已有 Feature

    ↓ 否
是否页面专属？
    ↓ 是
views / page-local

    ↓ 否
是否跨业务 UI？
    ↓ 是
components

    ↓ 否
是否跨业务组合能力？
    ↓ 是
composables

    ↓ 否
是否 API / Transport？
    ↓ 是
api / services

    ↓ 否
是否纯技术函数？
    ↓ 是
utils
```

不能仅因为“多个地方 import”就把代码升级为全局公共模块。

---

## 8. Component 规则

组件分为：

```text
Page / View
    = 页面编排

Feature Component
    = 业务 UI

Shared Component
    = 无业务语义的公共 UI
```

### Props / Emits

必须：

```text
明确类型
明确默认值
明确 nullable / optional
明确 Emit payload
```

禁止：

```text
any
隐式对象结构
深层 $parent
全局变量通信
DOM 查询替代组件通信
```

组件同时出现大量：

```text
API
状态机
表单规则
数据转换
复杂计算
```

应拆分 composable / service / 子组件。

---

## 9. Composable 规则

Composable 必须表达明确能力：

```text
usePagination()
usePolling()
usePermission()
useWorkflowExecution()
```

禁止：

```text
useCommon()
useUtils()
useEverything()
```

异步 composable 必须考虑：

```text
loading
success
error
cancel
stale request
unmount cleanup
retry
```

带副作用的 composable 必须定义创建与销毁边界。

---

## 10. 状态管理规则

状态必须先判断所有权：

```text
组件局部状态
 ↓
页面状态
 ↓
Feature 状态
 ↓
跨 Feature 客户端状态
 ↓
服务端状态 / Cache
```

能在组件解决，不进入 Store；能在 Feature 解决，不进入全局 Store。

### Pinia

Store 不得成为：

```text
万能 API 层
万能 Service
页面临时状态仓库
所有业务状态总线
```

Store Action 应有明确副作用边界。

服务端状态不要在多个 Store 中无约束复制。

---

## 11. API Contract

标准链路：

```text
Backend OpenAPI / Contract
        ↓
Generated / Synchronized Types
        ↓
API Client
        ↓
Feature API / Service
        ↓
Composable / Store
        ↓
View
```

禁止：

```text
View → fetch/axios → 手写 URL → any
```

不得直接把后端 ORM Model 当作前端 Contract。

API 类型必须集中、可追踪、可搜索。

---

## 12. API Client 统一规范

统一 HTTP 层负责：

```text
Base URL
Authentication
Request ID / Correlation ID
Timeout
Cancellation
Serialization
Error normalization
```

Retry 规则：

```text
幂等 / 安全请求
    → 可按策略 retry

非幂等 mutation
    → 默认禁止自动 retry
    → 只有具备明确幂等语义才能 retry
```

禁止每个页面创建独立 HTTP Client。

---

## 13. 请求竞态与取消

搜索、筛选、分页、详情切换、轮询必须考虑：

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

可使用：

```text
AbortController
Request Sequence
Latest-only
Debounce / Throttle
Query Cache / Deduplication
```

组件卸载后必须停止不再需要的请求、轮询和订阅。

---

## 14. 表单规则

表单至少明确：

```text
Initial
Dirty
Validating
Submitting
Success
Error
Reset / Cancel
```

区分：

```text
UI Validation
Business Validation
Backend Validation
```

前端校验不能成为安全边界。

重复提交必须受到控制。

---

## 15. Router 规则

Router 负责：

```text
Route Definition
Route Metadata
Authentication Entry
Authorization Entry
Navigation Prerequisite
```

禁止 Router Guard 承担完整业务流程。

Route Metadata 可以描述：

```text
permission
layout
title
authentication requirement
```

真实授权仍由 Backend 执行。

---

## 16. 权限与多租户

必须明确：

```text
Route Permission
Page Permission
Action Permission
Resource Scope
Tenant Scope
```

前端：

```text
显示 / 隐藏
禁用
导航
用户提示
```

后端：

```text
真实授权
资源访问
租户隔离
```

禁止把可编辑的 `tenantId`、role、permission 等前端字段当成安全依据。

缓存、本地状态和 URL 参数也必须考虑租户边界。

---

## 17. Loading / Empty / Error 状态

异步功能至少具备：

```text
idle
loading
success
empty
error
```

复杂场景可以增加：

```text
refreshing
saving
retrying
stale
partial
conflict
permission-denied
```

不要仅使用：

```text
loading = true / false
```

表达完整业务状态。

---

## 18. Error Model

前端应统一识别：

```text
Network
Authentication
Authorization
Validation
Conflict
Business
Server
Unknown
```

用户提示和诊断信息必须分离：

```text
User Message
≠
Developer Diagnostic
```

生产环境禁止输出：

```text
Token
Secret
Password
Internal Stack Trace
敏感业务 Payload
```

---

## 19. Accessibility

新组件至少考虑：

```text
Semantic HTML
Keyboard
Visible Focus
Focus Management
Label Association
ARIA
Screen Reader
Error Announcement
```

Dialog / Drawer / Menu 等组件必须定义焦点进入、焦点返回和 Escape 行为。

错误不能只通过颜色表达。

---

## 20. Responsive / UI

新页面必须考虑：

```text
Desktop
Tablet / Narrow viewport
Mobile（项目适用时）
```

复杂表格、工具栏、侧栏等应明确：

```text
折叠
滚动
重排
分页
分组
```

不要仅通过缩小字体解决窄屏问题。

---

## 21. Design System

推荐层级：

```text
Design Tokens
 ↓
Base Components
 ↓
Shared Components
 ↓
Feature Components
 ↓
Views
```

新增组件前必须检查已有能力：

```text
是否已经存在？
是否只是 Variant？
是否应该扩展现有组件？
是否真的需要新组件？
```

禁止出现多个语义相同但 API 不兼容的 Button、Dialog、Table、Form 等基础组件。

---

## 22. 国际化

支持 i18n 的项目中，用户可见文本禁止硬编码。

推荐：

```text
Feature Namespace
 ↓
Locale Resource
 ↓
Typed Translation Key（适用时）
```

同时考虑：

```text
Plural
Date / Time
Number
Currency
Long Text
RTL（需要时）
```

业务文案不要无边界堆积到单一全局 locale 文件。

---

## 23. 文件上传 / 下载

必须考虑：

```text
Type
Size
Progress
Cancel
Retry
Resume（需要时）
Server Validation
Permission
Filename Safety
```

大文件不得无意义地转换为 Base64 存入 Store。

敏感文件必须通过后端授权访问。

---

## 24. 大数据量列表

必须评估：

```text
Server Pagination
Server Filtering
Server Sorting
Virtualization
Incremental Loading
```

大量导出推荐：

```text
Create Export Task
 ↓
Backend Processing
 ↓
Status / Progress
 ↓
Download
```

不要一次性将不可控规模的数据全部加载到浏览器。

---

## 25. 实时通信

WebSocket / SSE 必须明确：

```text
Connection Lifecycle
Authentication
Reconnect
Backoff
Heartbeat
Message Schema
Ordering
Duplicate Handling
Cleanup
```

推荐：

```text
Transport
 ↓
Feature Event Handler
 ↓
State
 ↓
UI
```

不要在页面组件内堆积完整连接生命周期管理。

---

## 26. 前端缓存

缓存必须定义：

```text
Key
Scope
TTL
Invalidation
Version
Tenant Boundary
Permission Boundary
```

写操作后明确：

```text
Invalidate
Refetch
Patch Cache
```

禁止无期限缓存业务数据。

---

## 27. 性能规范

优化优先级：

```text
减少请求
 ↓
减少 Payload
 ↓
缓存 / 去重
 ↓
Code Splitting
 ↓
Lazy Loading
 ↓
降低响应式成本
 ↓
Rendering Optimization
```

大型 Feature 评估：

```text
Bundle Size
Initial Load
Chunk Size
Network
Rendering
Memory
Long Task
```

禁止无指标地滥用：

```text
shallowRef
markRaw
memo
缓存
```

---

## 28. TypeScript 规范

推荐：

```json
{
  "strict": true
}
```

默认禁止：

```ts
any
as any
// @ts-ignore
```

如果确有必要：

```text
局部隔离
说明原因
最小范围
增加测试
```

优先使用：

```text
unknown + type guard
Discriminated Union
Generic
Utility Types
satisfies
```

业务状态机优先用联合类型表达合法状态。

---

## 29. 安全规范

禁止：

```text
Secret / API Key 写入源码
Token 写入日志
生产凭据提交 Git
不可信内容直接 v-html
敏感数据进入 URL
前端权限代替后端权限
```

前端构建变量默认视为可能暴露给浏览器：

```text
VITE_* / PUBLIC_* 等
```

不得把 Secret 放入公开构建变量。

涉及 XSS、CSRF、CSP、Token Storage、文件上传等问题时必须进行专项安全评估。

---

## 30. 日志与可观测性

日志用于诊断，不是业务数据仓库。

推荐关联：

```text
request_id
trace_id
route
feature
operation
error_code
```

禁止记录：

```text
Access Token
Refresh Token
Password
Secret
完整敏感 Payload
```

生产日志应控制噪声和采样策略。

---

## 31. 测试分层

```text
Unit
 ↓
Component
 ↓
Integration
 ↓
E2E
```

### Unit

测试：

```text
Pure Function
Business Rule
Composable Logic
Data Transformation
```

### Component

测试：

```text
Props
Emit
Rendering
Interaction
Validation
Loading / Error
```

### Integration

测试：

```text
Feature + API Client
Feature + Store
Feature + Router
Contract Boundary
```

### E2E

只覆盖关键用户旅程：

```text
Login
Create
Edit
Submit
Critical Workflow
Permission
Recovery
```

避免所有测试都升级为 E2E。

---

## 32. Mock 与 Contract

Mock 用于隔离边界，不用于掩盖真实 Contract 问题。

必须避免：

```text
Mock Response ≠ Production Contract
```

重要 API 至少存在一层：

```text
Contract Test
或
Integration Test
```

Mock Fixture 应尽可能复用正式类型。

---

## 33. 测试环境与编排

测试代码与环境编排分离：

```text
src/**/*.spec.ts
frontend/tests/
frontend/scripts/
```

测试脚本必须明确：

```text
准备什么环境
启动什么服务
使用什么地址
如何清理
```

不得偷偷修改开发者本地环境或真实生产资源。

测试结果必须记录真实执行结果，不得用静态文案代替测试证据。

---

## 34. 依赖管理

新增 npm 依赖前必须确认：

```text
现有依赖是否已有能力？
维护状态
安全风险
License
Bundle Size
Tree Shaking
TypeScript 支持
```

不要为了一个简单函数引入大型依赖。

UI、State、HTTP 等基础框架级依赖必须评估长期影响。

---

## 35. 环境配置

明确区分：

```text
Build-time Config
Runtime Config
Public Config
Secret
```

浏览器可访问的配置不属于 Secret。

环境变量命名应统一，避免同一含义出现多个变量名称。

生产环境配置必须由部署系统注入，禁止提交真实凭据。

---

## 36. Refactor 规则

重构采用：

```text
识别依赖
 ↓
设计新边界
 ↓
迁移引用
 ↓
迁移测试
 ↓
删除旧实现
 ↓
全仓搜索旧路径
 ↓
验证 Build / Test
```

禁止长期保留：

```text
legacy/
old/
compat/
adapter-only forwarding
```

来掩盖迁移未完成。

如果只是目录治理，不得因为“看起来更标准”而制造大规模无业务收益的迁移。

---

## 37. 新 Feature 扩展准则

新增业务优先遵循：

```text
检查现有实现
 ↓
复用已有 API / Component / Composable
 ↓
确定业务边界
 ↓
在现有目录内最小扩展
 ↓
复杂度达到阈值
 ↓
引入 features/<domain>
```

Feature 内可以使用：

```text
api/
components/
composables/
stores/
types/
views/
```

Feature 不应直接暴露内部实现。

推荐：

```text
features/order/index.ts
```

作为稳定公共入口，避免其他 Feature 深度 import：

```text
❌ features/order/components/internal/xxx
❌ features/order/stores/privateStore
```

---

## 38. Feature 间依赖

推荐依赖方向：

```text
Feature A
   ↓
Feature B Public API
```

避免：

```text
Feature A ↔ Feature B
```

出现循环依赖时，应考虑：

```text
重新划分边界
提取稳定 Contract
共享纯类型 / UI Pattern
事件 / Command 解耦
```

不要用全局 Store 偷渡跨 Feature 依赖。

---

## 39. Breaking Change

以下变化需要进行影响评估：

```text
Props 删除 / 重命名
Emit Payload 改变
Store State / Action 改变
Composable API 改变
Route 改变
API Contract 改变
Permission 改变
Design Token 改变
公共组件行为改变
```

公共 API 变化优先提供迁移方案。

---

## 40. 删除 / 废弃规则

删除功能必须同时检查：

```text
Route
Menu
View
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

废弃能力必须记录：

```text
替代方案
迁移范围
删除条件
最终删除版本 / 时间（项目适用时）
```

---

## 41. Code Review 检查清单

Review 至少检查：

```text
[ ] 目录归属合理
[ ] 是否重复实现已有能力
[ ] API Contract 是否一致
[ ] TypeScript 类型是否完整
[ ] State 边界是否合理
[ ] 是否出现跨层依赖
[ ] Permission 是否正确
[ ] Error / Loading / Empty 是否完整
[ ] Accessibility 是否考虑
[ ] Responsive 是否考虑
[ ] 是否存在竞态 / 重复提交
[ ] 是否存在安全问题
[ ] 测试是否覆盖关键行为
[ ] 是否产生无必要的新依赖
[ ] 是否留下 dead code
```

---

## 42. Definition of Done

前端功能完成必须满足适用项：

```text
[ ] 业务边界明确
[ ] 目录归属明确
[ ] Backend Contract 对齐
[ ] TypeScript 类型完整
[ ] API Client 完成
[ ] State 边界明确
[ ] View / Component 完成
[ ] Loading / Empty / Error 完成
[ ] Permission 已考虑
[ ] Accessibility 已考虑
[ ] Responsive 已考虑
[ ] Error / Observability 完成
[ ] Unit / Component Test 完成
[ ] Integration Test（适用时）
[ ] E2E（关键路径）
[ ] Type Check
[ ] Lint
[ ] Production Build
[ ] 无重复实现
[ ] 无 Secret 泄漏
[ ] 文档更新
[ ] Git 变更可追踪
```

---

## 43. Git 与 Commit

推荐：

```text
feat(frontend): ...
fix(frontend): ...
refactor(frontend): ...
test(frontend): ...
chore(frontend): ...
```

一个 Commit 尽量对应一个工程变化。

禁止将以下无关变化混在一起：

```text
业务功能
大规模格式化
依赖升级
目录重构
```

除非这些变化确实属于同一个不可拆分的迁移。

---

## 44. 通用项目与项目实现的关系

```text
UNIVERSAL_DEVELOPMENT_GUIDELINES.md
            ↓
Vue + TypeScript 通用准则
            ↓
项目 DEVELOPMENT.md
            ↓
当前项目目录与技术选型
            ↓
Feature / Architecture Design
            ↓
Implementation
            ↓
Test Gate
            ↓
Acceptance
```

通用准则解决：

```text
应该如何工程化
```

项目准则解决：

```text
本项目具体怎么落地
```

因此：

> **通用准则不应该推翻已有项目目录，而应该规定已有目录如何稳定演进，以及新功能何时、为什么、如何扩展。**

---

## 45. 最终架构原则

当前项目以及后续 Vue + TypeScript 项目统一遵循：

```text
保留稳定架构
      ↓
明确目录职责
      ↓
新增功能最小扩展
      ↓
避免跨层依赖
      ↓
业务增长后按边界拆分
      ↓
必要时 Feature 化
      ↓
持续删除旧实现
```

最终目标不是让目录越来越多，而是让：

```text
业务边界清晰
依赖方向清晰
状态边界清晰
Contract 清晰
公共能力稳定
Feature 可以独立演进
测试可以定位问题
重构可以逐步进行
```

**任何架构调整都必须以降低长期复杂度为目标，而不是为了满足某一种“标准目录”而调整目录。**
