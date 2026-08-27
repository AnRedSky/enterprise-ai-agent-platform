# Vue + TypeScript 前端通用项目开发准则

> **定位**：本文件定义 Vue 3 + TypeScript 企业级前端项目的通用工程基线，并以当前项目已经采用的 `frontend/src/api`、`router`、`utils`、`views` 等目录作为落地参考。
>
> **重要原则**：本准则是通用规范，不要求所有项目立即迁移为某一种 Feature First 目录。对于已有项目，应保留既有目录架构、职责和稳定 API，通过新增功能逐步收敛边界；只有业务规模和依赖复杂度达到拆分条件时，才引入 `features/<domain>` 等更细粒度结构。
>
> 本文件遵循 `UNIVERSAL_DEVELOPMENT_GUIDELINES.md`。项目级 `DEVELOPMENT.md` 可以补充具体 UI 组件库、目录实例、命令、CI/CD 和部署环境，但不得无故违反本文件的核心工程原则。

---

## 1. 核心原则

1. **Contract First**：前端 API 类型以正式 Backend Contract 为准，优先从 OpenAPI 等契约生成或同步类型。
2. **Incremental Architecture**：基于现有目录持续演进，不因架构规范而进行无收益的大规模目录迁移。
3. **Modular First**：代码按职责和业务边界组织，模块必须具备清晰的公开接口、内部实现和依赖方向。
4. **Feature Boundary**：新增业务必须有清晰边界；规模较小时可落在现有 `api/views/utils`，规模增长后再按 Feature 聚合。
5. **State Boundary**：区分组件状态、页面状态、业务共享状态、服务端状态和持久化状态。
6. **UI / Business Separation**：View 和 Component 负责展示与交互编排，业务规则进入可测试的 composable / service / domain logic。
7. **Type First**：TypeScript 使用严格类型；禁止通过 `any`、`as any` 或 `@ts-ignore` 长期绕过类型系统。
8. **Security Boundary**：前端权限控制只负责 UX；真正授权、租户隔离和资源访问必须由后端执行。
9. **Observable UI**：异步操作必须具备 Loading / Success / Empty / Error 等可观测状态。
10. **Accessible by Default**：新交互默认支持键盘、焦点、语义化 HTML 和辅助技术。
11. **Measured Performance**：性能优化必须有问题、指标、方案和验证结果。
12. **Testable Delivery**：测试按照 Unit / Component / Integration / E2E 的风险和边界分层。
13. **Small and Traceable Changes**：一个提交尽量对应一个可解释的工程变化。
14. **Stable Module Entry**：目录级 UI 模块统一以 `index.vue` 作为 UI 入口；内部组件保持语义化命名。

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

具体项目可以替换实现，但必须提供等价能力：类型检查、代码规范、单元/组件测试、关键浏览器流程测试、生产构建验证。

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

这是当前项目基线，不是要求所有项目必须完全复制的模板。

随着项目增长，可以在不破坏既有目录职责的前提下逐步增加：

```text
src/
├── app/                   # 应用启动、插件、全局配置
├── api/                   # 全局 API / Contract 接入能力
├── router/                # 路由与导航
├── components/            # 真正跨业务复用的 UI
├── composables/           # 跨业务稳定组合式能力
├── layouts/               # 页面布局模块
├── services/              # 跨业务技术服务
├── stores/                # 真正全局客户端状态
├── types/                 # 全局技术类型
├── utils/                 # 无业务语义的纯工具
├── styles/                # 全局样式 / Design Tokens
├── views/                 # 页面模块
└── features/              # 业务规模达到条件后按领域聚合
    └── <domain>/
```

**禁止为了“完整目录”预先创建大量空目录。**

---

## 4. 模块化设计总则

模块化不是简单地拆目录，而是建立：

```text
职责边界
+
公开接口
+
内部实现
+
依赖方向
+
状态所有权
+
测试边界
```

一个模块应能够回答：

```text
我负责什么？
我不负责什么？
我向外暴露什么？
我依赖谁？
谁可以依赖我？
我的状态由谁拥有？
如何独立测试？
```

### 模块最小闭环

推荐：

```text
Module
├── UI Entry / index.vue（存在 UI 时）
├── Programmatic Public API / index.ts（存在跨模块程序化能力时）
├── Types / Contract
├── Implementation
├── Tests
└── Documentation（复杂模块需要）
```

模块不要求机械创建全部文件；只创建实际需要的部分。

### 4.1 目录即模块边界

目录级模块采用：

```text
<module>/
└── index.vue
```

约定：

```text
目录 = 模块边界
index.vue = 模块 UI 入口
index.ts = 程序化 Public API
语义化文件名 = 内部实现
```

`index.vue` 只作为目录级模块入口，不要求所有 `.vue` 文件统一命名为 `index.vue`。

### 4.2 模块入口稳定性

模块内部可以逐步增加：

```text
components/
composables/
stores/
api/
types/
constants/
utils/
```

但外部入口保持稳定：

```text
module/index.vue
```

这样模块可以从简单页面逐步演进为复杂业务模块，而不需要同步修改 Router 或大量调用方。

---

## 5. Layout / View / Feature 分层模型

通用 Vue + TypeScript 项目推荐形成：

```text
App / Bootstrap
      ↓
Router
      ↓
Layout / index.vue
      ↓
View / index.vue
      ↓
Feature / index.vue
      ↓
Feature Components / Composables / Store / API
      ↓
Shared / Services / Infrastructure
```

### Layout

Layout 是 **Application Shell / Page Frame**，负责页面空间结构：

```text
Header
Sidebar
Navigation
Breadcrumb
Tabs
Footer
Content Container
Responsive Layout
RouterView
```

Layout 不负责具体业务：

```text
❌ User 查询
❌ Order 业务规则
❌ Workflow 状态机
❌ Feature API 调用
```

推荐：

```text
layouts/
└── app/
    ├── index.vue
    ├── components/
    │   ├── AppHeader.vue
    │   ├── AppSidebar.vue
    │   ├── AppBreadcrumb.vue
    │   └── AppTabs.vue
    └── composables/
        └── useAppLayout.ts
```

### View

View 是 **Page / Screen**，负责一个具体页面的组合与页面级交互：

```text
路由参数接入
页面级状态
页面级交互
Feature 组合
页面 Loading / Empty / Error 展示
```

View 不负责：

```text
❌ 全局布局
❌ 底层 HTTP Client
❌ 大型业务规则
❌ 跨页面全局状态
```

推荐：

```text
views/
└── users/
    ├── index.vue
    ├── components/
    ├── composables/
    ├── api/
    └── types/
```

### Feature

Feature 是 **Business Capability**，负责完整业务能力：

```text
业务 UI
业务组件
业务状态
业务 API
业务 Composable
业务类型
业务规则
```

推荐：

```text
features/
└── user/
    ├── index.vue
    ├── index.ts
    ├── components/
    ├── composables/
    ├── stores/
    ├── api/
    ├── types/
    ├── constants/
    └── utils/
```

### 三者关系

```text
Layout
= 页面怎么摆

View
= 这一页是什么

Feature
= 这一页背后的业务能力
```

简单项目不要求同时存在三层；只有当边界真正出现时才增加层次。

---

## 6. 模块入口统一 `index.vue`

以下目录级 UI 模块统一采用 `index.vue`：

```text
layouts/
├── app/
│   └── index.vue
├── auth/
│   └── index.vue
└── fullscreen/
    └── index.vue

views/
├── dashboard/
│   └── index.vue
├── users/
│   └── index.vue
└── settings/
    └── index.vue

features/
└── workflow/
    ├── index.vue
    ├── index.ts
    ├── components/
    ├── composables/
    └── api/
```

### `index.vue` 的职责

```text
模块 UI Composition Root
```

允许：

```text
Layout / Template Composition
Props 接入
Route 参数接入
Feature Component 组合
Composable 编排
页面级状态展示
页面级事件处理
```

不应长期承载：

```text
底层 HTTP 实现
大型业务规则
复杂数据转换
跨 Feature 全局状态
WebSocket 生命周期
复杂轮询机制
大量纯函数
```

复杂逻辑应下沉到对应模块：

```text
components/
composables/
stores/
api/
services/
utils/
```

### 内部组件命名

只有目录级模块入口使用 `index.vue`；内部组件必须保持语义化命名：

```text
components/
├── UserTable.vue
├── UserForm.vue
├── UserDetail.vue
└── UserToolbar.vue
```

禁止把所有组件都命名为 `index.vue`。

---

## 7. 当前目录到模块化目录的演进

当前项目可以保持：

```text
src/
├── api/
├── router/
├── utils/
└── views/
```

一个简单页面：

```text
views/users/
└── index.vue
```

复杂后逐步增加：

```text
views/users/
├── index.vue
├── components/
├── composables/
├── api/
└── types/
```

当业务需要独立 Feature 边界时：

```text
features/users/
├── index.vue
├── index.ts
├── components/
├── composables/
├── stores/
├── api/
├── types/
└── utils/
```

关键原则：

> **增加模块化能力，而不是强制重构已有目录。**

旧结构稳定且规模可控时，可以继续使用；只有边界问题真正出现时才进行局部迁移。

---

## 8. Feature Module 推荐结构

```text
features/
└── <domain>/
    ├── index.vue              # UI Entry
    ├── index.ts               # Programmatic Public API（需要时）
    ├── api/                   # Feature API
    ├── components/            # Feature UI
    ├── composables/           # Feature 行为
    ├── stores/                # Feature 共享状态
    ├── types/                 # Feature 类型
    ├── views/                 # Feature 页面子模块（需要时）
    ├── constants/             # Feature 私有常量
    └── utils/                 # Feature 私有纯函数
```

不是每个 Feature 都必须创建所有目录。

Feature 的 UI 入口统一：

```text
features/<domain>/index.vue
```

程序化 Public API：

```text
features/<domain>/index.ts
```

两者职责不同：

```text
index.vue = UI Composition Root
index.ts   = Programmatic Public API
```

---

## 9. Feature Public API

Feature 应通过 `index.ts` 定义公开的程序化能力：

```ts
import { OrderList } from '@/features/order'
```

而 UI 入口使用：

```text
features/order/index.vue
```

外部模块禁止：

```text
features/order/components/internal/*
features/order/stores/private/*
```

优先依赖模块公开入口。

Public API 应尽量只暴露：

```text
Public Components
Public Composables
Public Types
Public Commands / Actions
```

不应暴露内部 API Client、私有状态结构等实现细节。

---

## 10. 模块依赖方向

推荐：

```text
app
 ↓
router
 ↓
layouts
 ↓
views
 ↓
features
 ↓
shared / services
 ↓
transport / browser / external SDK
```

禁止：

```text
utils → feature
shared component → page
service → view
API client → component
feature A internal → feature B internal
```

如果出现循环依赖：

```text
A → B
B → A
```

优先：

```text
提取 Shared Contract
调整模块边界
通过 Event / Command 解耦
```

而不是增加更多全局状态掩盖依赖问题。

---

## 11. 模块内部依赖规则

Feature 内部推荐：

```text
index.vue / views
 ↓
components / composables
 ↓
api / service / store
 ↓
shared infrastructure
```

同一层级模块之间尽量避免直接互相依赖。

如果两个组件需要共享能力，应提取为明确的公共能力，而不是互相引用内部实现。

---

## 12. 模块状态所有权

每个状态必须有唯一合理的 Owner：

```text
Component State
    ↓
Page State
    ↓
Feature State
    ↓
Global State
    ↓
Server State / Cache
```

规则：

```text
能局部解决 → 不上升
能 Page 解决 → 不进入全局 Store
能 Feature 解决 → 不全局化
能服务端获取 → 不重复复制多份
```

避免同一业务数据同时存在多个状态源而没有明确同步规则。

---

## 13. 模块 API 与 Contract

模块之间也应该采用 Contract First：

```text
Public Types
Public Props
Public Emits
Public Functions
Public Events
```

内部结构变化不能无故影响外部调用方。

公共模块升级应考虑：

```text
Backward Compatibility
Migration Path
Deprecation
Breaking Change
```

---

## 14. 模块间通信

优先级：

```text
Props / Emits
 ↓
Composable
 ↓
Explicit Function API
 ↓
Feature Store
 ↓
Event / Message
```

禁止优先使用：

```text
window 全局变量
DOM 查询
$parent / $children
任意全局事件总线
```

Event Bus 仅适用于明确的跨模块事件场景，并必须定义 Event Contract 和生命周期。

---

## 15. Shared 模块治理

公共模块不是“所有东西的最终归宿”。

代码进入 Shared 必须满足：

```text
至少存在明确的跨模块使用场景
+
职责稳定
+
没有具体业务归属
+
公开 API 可维护
```

如果只有一个 Feature 使用：

```text
优先保留在 Feature 内
```

不能因为 import 数量增加就机械升级为 Shared。

---

## 16. 模块拆分条件

满足以下任一情况，可以考虑拆分：

```text
模块超过合理复杂度
单文件承担多个职责
业务状态和 UI 高度耦合
多个开发者频繁冲突
测试难以隔离
依赖图复杂
发布 / 演进需要独立边界
```

尤其当 `index.vue` 出现：

```text
大量模板
多个复杂区域
多个异步流程
大量业务规则
多个独立交互流程
```

应优先拆到：

```text
components/
composables/
stores/
api/
services/
```

而不是继续无限扩大 `index.vue`。

---

## 17. 模块合并条件

模块化同样允许合并。

当两个模块：

```text
职责高度一致
生命周期一致
总是一起修改
不存在独立使用场景
```

应考虑合并，避免过度碎片化。

原则：

> **模块数量不是架构质量指标，边界质量才是。**

---

## 18. API / Router / Layout / View / Feature 协作

推荐完整链路：

```text
Router
 ↓
Layout/index.vue
 ↓
View/index.vue
 ↓
Feature/index.vue
 ↓
Feature API / Composable / Store
 ↓
Shared HTTP Client
 ↓
Backend Contract
```

View 不直接实现底层 HTTP 细节。

API 层不负责 UI 状态。

Router 不负责业务流程。

Layout 不负责具体业务。

---

## 19. API 层规则

`api/` 负责：

```text
Endpoint
Request DTO
Response DTO
Contract Adapter
```

不负责：

```text
页面状态
DOM
复杂业务流程
```

随着规模增长，可以演进为：

```text
api/
├── client.ts
├── interceptors.ts
└── <domain>/
    ├── <domain>.api.ts
    └── types.ts
```

Feature 化后优先：

```text
features/<domain>/api/
```

---

## 20. Router 模块化

路由规模增长后不要继续维护单一巨大 `router.ts`。

可以采用：

```text
router/
├── index.ts
├── guards.ts
├── routes.ts
└── modules/
    ├── auth.routes.ts
    ├── user.routes.ts
    └── workflow.routes.ts
```

路由页面优先指向模块入口：

```ts
{
  path: '/users',
  component: () => import('@/views/users/index.vue')
}
```

Layout：

```ts
{
  path: '/admin',
  component: () => import('@/layouts/app/index.vue'),
  children: [
    {
      path: 'users',
      component: () => import('@/views/users/index.vue')
    }
  ]
}
```

Route Guard 只处理导航级职责。

---

## 21. Store 模块化

小型项目：

```text
stores/
└── auth.ts
```

中大型项目：

```text
stores/
├── auth/
│   └── index.ts
├── app/
│   └── index.ts
└── preferences/
    └── index.ts
```

Feature 状态：

```text
features/<domain>/stores/
```

禁止创建一个包含所有业务状态的 `appStore`。

---

## 22. Services 模块化

`services/` 应定位为技术服务，而不是业务万能 Service。

推荐：

```text
services/
├── http/
├── storage/
├── upload/
├── download/
└── websocket/
```

业务能力优先进入：

```text
features/<domain>/
```

---

## 23. Utils 模块化

全局：

```text
utils/
├── date.ts
├── number.ts
├── string.ts
├── object.ts
└── validation.ts
```

Feature 私有：

```text
features/order/utils/
```

工具函数必须：

```text
低副作用
无 UI 依赖
无 Store 依赖
无业务生命周期
可独立测试
```

禁止万能 `utils/index.ts` 承载所有业务逻辑。

---

## 24. 组件分层

```text
UI Primitive
 ↓
Shared Component
 ↓
Feature Component
 ↓
View / Page
```

例如：

```text
Button
 ↓
DataTable
 ↓
OrderTable
 ↓
Order View/index.vue
```

越靠下越接近业务，越靠上越通用。

---

## 25. 新功能模块化扩展流程

新增功能必须执行：

```text
1. 阅读项目 DEVELOPMENT.md
2. 同步最新代码
3. 搜索已有模块
4. 判断是否属于现有模块 / Feature
5. 确定模块边界
6. 确定 UI Entry：<module>/index.vue
7. 定义 Public Contract
8. 定义 Type / DTO
9. 实现 API / Service
10. 实现 State / Composable
11. 实现 Component / index.vue
12. 接入 Router / Permission
13. 完善 Loading / Empty / Error
14. Accessibility / Responsive
15. Unit / Component Test
16. Integration / E2E（适用时）
17. Type Check / Lint / Build
18. 更新文档
19. Review / Commit
```

---

## 26. 新功能目录选择决策表

| 新增内容 | 小规模项目 | 中大型项目 | UI 入口 |
|---|---|---|---|
| 页面 | `views/<domain>/` | `features/<domain>/views/` | `index.vue` |
| 业务模块 | `views/<domain>/` | `features/<domain>/` | `index.vue` |
| Layout | `layouts/<layout>/` | `layouts/<layout>/` | `index.vue` |
| 业务组件 | 页面邻近 / Feature | Feature `components/` | 语义化 `*.vue` |
| 公共 UI | `components/` | `components/` | 按组件语义命名 |
| API | `api/` | Feature `api/` | 无 |
| Composable | `composables/` | Feature `composables/` | 无 |
| Store | `stores/` | Feature `stores/` | 无 |
| 技术 Service | `services/` | `services/<domain>/` | 无 |
| 类型 | `types/` | Feature `types/` | 无 |
| 工具 | `utils/` | Feature `utils/` | 无 |
| 路由 | `router/` | `router/modules/` | `index.ts` |
| 样式 | `styles/` | `styles/` | 无 |

---

## 27. 其他通用工程规则

### Component

Props / Emits 必须明确类型；禁止深层组件通信、DOM 查询通信和隐式全局状态。

### Composable

必须明确生命周期、响应式依赖、取消、错误和清理。

### State

不要把所有状态放入 Pinia；服务端状态与客户端状态分开管理。

### API

HTTP Client 统一处理 Base URL、认证、Request ID、Timeout、Cancellation、Error Normalization 和安全 Retry。

### Retry

非幂等 Mutation 默认禁止自动重试，除非 Contract 明确支持幂等。

### Form

区分 UI Validation、Business Validation、Backend Validation。

### Permission

前端只负责 UX；后端负责真正授权。

### Async

必须处理 Loading、Error、Cancellation、Stale Response、Unmount Cleanup。

### Realtime

WebSocket / SSE 必须考虑连接生命周期、Reconnect、Backoff、Ordering、Duplicate 和 Cleanup。

### Accessibility

遵循语义化 HTML、Keyboard、Focus、ARIA 和错误反馈原则。

### Performance

基于真实指标进行优化，重点关注请求、Bundle、渲染、内存和大列表。

### Security

禁止 Secret / Token 进入源码或日志；不可信 HTML 必须经过安全处理。

### i18n

用户可见文本不得散落硬编码；Feature 文案优先按领域组织。

### Testing

按照 Unit / Component / Integration / E2E 分层，不为覆盖率机械重复测试。

---

## 28. 模块化重构规则

禁止一次性“大搬家”而没有收益验证。

标准流程：

```text
现状分析
 ↓
依赖图
 ↓
定义目标边界
 ↓
建立新 Public API
 ↓
保持 index.vue 作为 UI Entry
 ↓
迁移调用方
 ↓
迁移测试
 ↓
删除旧实现
 ↓
全仓搜索旧引用
 ↓
Type Check
 ↓
Test
 ↓
Build
```

重构必须保持：

```text
行为不变
Contract 稳定
入口稳定
测试不下降
旧实现最终删除
```

---

## 29. 模块质量检查

一个模块至少检查：

```text
[ ] 职责单一
[ ] 边界明确
[ ] index.vue UI Entry 明确（存在 UI 时）
[ ] index.ts Public API 明确（存在程序化能力时）
[ ] 内部实现可隐藏
[ ] 依赖方向正确
[ ] 无循环依赖
[ ] 状态 Owner 明确
[ ] Contract 明确
[ ] 可独立测试
[ ] 无重复实现
[ ] 无无主代码
```

---

## 30. Definition of Done

前端功能只有同时满足适用项才算完成：

```text
[ ] Feature / Module boundary clear
[ ] UI Entry / index.vue clear when applicable
[ ] Contract aligned
[ ] Type complete
[ ] Permission considered
[ ] Loading / Empty / Error handled
[ ] Accessibility considered
[ ] Responsive considered
[ ] Unit / Component tests
[ ] Integration test when required
[ ] E2E for critical path
[ ] Production build
[ ] No duplicate implementation
[ ] No secret leakage
[ ] Documentation updated
[ ] Git change traceable
```

---

## 31. 禁止事项

```text
❌ 为了规范强制迁移全部旧目录
❌ 所有 Vue Component 都命名为 index.vue
❌ 一个万能 Store
❌ 一个万能 utils.ts
❌ 一个万能 service.ts
❌ View/index.vue 内堆积全部业务逻辑
❌ Layout/index.vue 内堆积具体业务逻辑
❌ 页面各自创建 HTTP Client
❌ Feature 深度依赖其他 Feature internal 文件
❌ Shared 模块依赖具体业务
❌ 前端权限代替后端权限
❌ 非幂等 API 无脑 retry
❌ Mock 长期脱离真实 Contract
❌ Secret / Token 进入源码或日志
❌ 只验证成功路径
❌ 用兼容层长期掩盖重构未完成
❌ 为了模块化而机械拆分文件
❌ 只写代码不更新 Contract / 文档
```

---

## 32. 与项目治理文档的关系

```text
UNIVERSAL_DEVELOPMENT_GUIDELINES.md
            ↓
Vue + TypeScript 通用准则
            ↓
项目 DEVELOPMENT.md
            ↓
Architecture / Feature Design
            ↓
Implementation
            ↓
Test Gate
            ↓
Acceptance
```

本文件解决：

> **Vue + TypeScript 项目应该如何进行工程化、模块化和模块入口设计。**

项目级文档负责补充具体 UI 框架、实际目录、命令、部署、CI 和测试环境。

最终目标不是让所有项目拥有完全相同的目录，而是让不同规模的 Vue + TypeScript 项目都能遵循：

```text
清晰边界
→ 明确职责
→ 稳定 Contract
→ 稳定 Module Entry
→ 单向依赖
→ 最小共享
→ 独立测试
→ 渐进式拆分
→ 可持续演进
```
