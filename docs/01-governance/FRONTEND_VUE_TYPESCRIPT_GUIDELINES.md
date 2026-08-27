# Vue + TypeScript 前端通用项目开发准则

> **定位**：本文件定义基于 Vue 3 + TypeScript 的企业级前端项目通用工程规范。它是可复制到其他 Vue + TypeScript 项目的技术开发基线，不记录具体项目阶段进度。
>
> 本文件遵循 `UNIVERSAL_DEVELOPMENT_GUIDELINES.md`。项目自身的 `DEVELOPMENT.md` 可以补充具体框架、目录、命令和部署约束，但不得无故违反本文件的核心工程原则。

---

## 1. 核心原则

1. **Contract First**：前端类型与 API Contract 必须来自后端正式契约，不允许长期手工维护第二套业务协议。
2. **Feature First**：按业务能力组织代码，而不是建立巨型 `components/`、`utils/`、`services/` 垃圾桶。
3. **状态有边界**：页面状态、组件状态、共享业务状态、服务端缓存状态必须明确区分。
4. **UI 不承载业务核心规则**：业务规则应进入可测试的 composable/domain/service 层。
5. **类型优先**：禁止用 `any` 掩盖 Contract、状态或第三方 SDK 类型问题。
6. **可访问性优先**：交互组件必须具备键盘、焦点、语义和错误反馈能力。
7. **性能可度量**：优化必须基于实际指标，不进行无依据的过早优化。
8. **可测试交付**：功能完成必须同时考虑 Unit、Component、Integration、E2E 的适用范围。

## 2. 推荐技术基线

```text
Vue 3
TypeScript strict mode
Vite
Vue Router
Pinia（仅在需要共享客户端状态时）
Vue Test Utils
Vitest
Playwright
ESLint
Prettier
```

具体项目可以替换技术组件，但必须保留等价能力：类型检查、组件测试、浏览器测试、代码规范和生产构建验证。

## 3. 推荐目录结构

```text
src/
├── app/                    # 应用启动、插件、全局配置
├── assets/                 # 静态资源
├── components/             # 真正跨 Feature 复用的 UI 组件
├── composables/            # 跨 Feature 的通用组合式能力
├── features/               # 业务 Feature，优先承载业务代码
│   └── <domain>/
│       ├── api/
│       ├── components/
│       ├── composables/
│       ├── stores/
│       ├── types/
│       ├── views/
│       └── index.ts
├── layouts/                # 页面布局
├── router/                 # 路由定义与导航守卫
├── services/               # 跨领域技术服务；业务逻辑不得集中于此
├── stores/                 # 仅放真正跨 Feature 的共享客户端状态
├── types/                  # 全局技术类型，不放具体业务垃圾
├── utils/                  # 无业务语义的纯工具
├── styles/                 # 全局样式、tokens
├── App.vue
└── main.ts
```

复杂项目优先 `features/<domain>`；禁止所有业务都直接堆入 `views/`、`components/` 或 `stores/`。

## 4. Feature 边界

一个 Feature 应能够独立解释：

```text
它解决什么业务问题？
它暴露什么 API？
它依赖哪些其他 Feature？
它维护什么状态？
它有哪些页面与组件？
```

推荐依赖方向：

```text
View
 ↓
Feature Component / Composable
 ↓
Feature API / Domain Service
 ↓
HTTP Client
 ↓
Backend Contract
```

禁止 View 直接拼接复杂请求、处理鉴权、修改多个共享 Store 或复制业务规则。

## 5. Vue Component 规则

组件必须拥有清晰的单一职责：

```text
Page / View
    = 页面编排

Feature Component
    = 业务 UI

Shared Component
    = 无业务语义的通用 UI
```

### Props / Emits

- Props 必须定义明确类型；
- Emit 必须定义事件 payload 类型；
- 不通过 `any`、`Record<string, unknown>` 泛滥传递未知结构；
- 不通过深层 `$parent`、全局变量或 DOM 查询跨组件通信；
- 组件内部状态不能被父组件隐式依赖。

### 组件大小

当组件同时包含大量：

```text
API 请求
状态机
表单校验
数据转换
复杂计算
大段模板
```

必须拆分 composable / service / 子组件，而不是继续堆积代码。

## 6. Composition API / Composable

Composable 应表达明确能力，例如：

```text
useWorkflowExecution()
usePagination()
usePermission()
usePolling()
```

禁止创建：

```text
useUtils()
useCommon()
useEverything()
```

Composable 必须明确生命周期、响应式依赖、清理逻辑和异常语义。

异步 composable 必须考虑：

```text
loading
success
error
cancel / stale request
unmount cleanup
retry
```

## 7. State Management

必须先判断状态属于哪一层：

```text
组件局部状态
    ↓
页面 / Feature 状态
    ↓
跨页面共享客户端状态
    ↓
服务端状态 / Cache
```

不要把所有状态都放入 Pinia。

### Pinia 使用原则

Store 应表达稳定业务状态或共享客户端状态，不应成为：

```text
API 请求垃圾桶
万能 Service
页面临时状态容器
```

Store action 必须有明确副作用边界，并避免组件之间互相调用形成循环依赖。

## 8. API Contract

前端 API 层必须围绕正式 Backend Contract 建立类型：

```text
Backend Contract
      ↓
Generated / manually synchronized DTO Types
      ↓
API Client
      ↓
Feature Service
      ↓
Composable
      ↓
View
```

推荐 OpenAPI 驱动类型生成；如果暂时无法生成，必须集中定义 DTO，不允许每个页面重复定义相同 Request / Response 类型。

禁止直接把后端数据库 ORM Model 当作前端 Contract。

## 9. API 请求规范

HTTP Client 应统一处理：

```text
Base URL
Authentication
Request ID / Correlation ID
Timeout
Cancellation
Serialization
Error normalization
Retry policy（仅对安全请求）
```

业务页面不得各自实现一套 HTTP Client。

### Retry

默认禁止对非幂等 mutation 自动重试。

```text
GET / safe request
    → 可按策略 retry

POST / mutation
    → 必须确认幂等语义后才能 retry
```

## 10. 异步与竞态

搜索、过滤、分页、详情切换等场景必须考虑旧请求覆盖新请求的问题。

推荐：

```text
request A
request B
   ↓
A 返回较晚
   ↓
禁止 A 覆盖 B
```

可使用 AbortController、request sequence、query cache 等机制解决。

## 11. 表单与校验

必须区分：

```text
UI 格式校验
    ≠
业务校验
    ≠
后端最终校验
```

前端校验用于即时反馈，不能作为安全边界。

错误必须关联具体字段或操作，并避免只显示无意义的“请求失败”。

## 12. 路由

路由必须保持声明式和集中管理。

路由守卫只能处理：

```text
Authentication
Authorization entry
Navigation prerequisite
```

不要在 Router Guard 中实现完整业务流程。

动态路由、权限菜单和按钮权限必须基于后端正式权限 Contract，不能仅依赖前端隐藏 UI 实现安全控制。

## 13. 权限与多租户

前端权限是 UX 层控制，不是安全边界。

必须遵循：

```text
Backend Authorization = Security Boundary
Frontend Authorization = UI / UX Boundary
```

租户 ID、角色、权限、资源范围不得由用户可控的前端字段直接决定后端权限。

## 14. 错误处理

统一建立 Error Model：

```text
Network Error
Authentication Error
Authorization Error
Validation Error
Conflict
Business Error
Server Error
Unknown Error
```

页面应针对用户可恢复错误给出操作建议；开发环境保留足够诊断信息，生产环境禁止泄漏 Secret、Token、内部堆栈和敏感业务数据。

## 15. Loading / Empty / Error / Success

所有异步页面必须明确至少：

```text
Loading
Success
Empty
Error
```

复杂操作还需要考虑：

```text
Partial Success
Retrying
Stale Data
Permission Denied
Conflict
```

禁止用 `loading=false` 作为唯一状态模型。

## 16. 可访问性

企业级前端至少遵循 WCAG 基本原则：

- 使用语义化 HTML；
- 所有键盘可操作控件具备可见焦点；
- Dialog / Drawer 正确管理焦点；
- 表单字段具有关联 label；
- 图片提供适当替代文本；
- 错误不能只依靠颜色表达；
- 动态内容需要合理的辅助技术通知。

## 17. 样式与 Design System

推荐建立：

```text
Design Tokens
 ↓
Base Components
 ↓
Feature Components
 ↓
Pages
```

禁止在业务页面大量复制相同 CSS。

颜色、间距、字体、圆角、阴影等核心视觉变量应集中管理。

组件库升级必须评估视觉回归与交互兼容性。

## 18. 性能规范

性能优化优先级：

```text
减少不必要请求
 ↓
减少传输数据
 ↓
缓存 / 去重
 ↓
代码分割
 ↓
组件懒加载
 ↓
减少无意义响应式依赖
 ↓
渲染优化
```

大型列表必须评估分页、虚拟滚动和增量加载。

禁止为了“性能”随意使用 `shallowRef`、`markRaw`、缓存或 memo，而不说明原因和验证指标。

## 19. 安全

禁止：

- 将 Secret / API Key 写入源码；
- 将 Token 写入日志；
- 使用 `v-html` 渲染不可信内容而无消毒；
- 将敏感数据放入 URL；
- 将权限判断当成后端安全控制；
- 将生产凭据提交 Git。

涉及 XSS、CSRF、CSP、Token 存储、文件上传等安全设计时必须采用项目安全规范并进行专项验证。

## 20. TypeScript 规则

推荐：

```json
{
  "strict": true
}
```

禁止：

```ts
any
as any
// @ts-ignore
```

除非存在明确技术原因，并必须局部隔离、注释原因和增加测试。

优先使用：

```text
unknown + type guard
interface / type
Discriminated Union
Generic
Utility Types
satisfies
```

业务状态机优先使用 Discriminated Union 表达合法状态，而不是大量可选字段。

## 21. 测试分层

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

测试纯函数、domain logic、composable 中可隔离的规则。

### Component

测试：

```text
Props
Events
Rendering
User interaction
Validation
Error state
```

### Integration

测试 Feature 与 API Client / Store / Router 等边界。

### E2E

只覆盖关键用户旅程，例如：

```text
Login
Create
Edit
Submit
Workflow
Permission
Critical recovery path
```

不要把所有 Unit / Component 测试重复搬到 E2E。

## 22. 测试隔离

测试实现与测试编排分离：

```text
src/**/*.spec.ts
frontend/tests/
frontend/scripts/test/
```

测试脚本不得偷偷启动、停止或修改真实服务，除非项目明确把它定义为环境编排职责。

测试结果只能记录实际执行结果。

## 23. Mock 规则

Mock 必须用于隔离明确边界，而不是掩盖真实 Contract 问题。

禁止：

```text
Mock Response 与真实 API Contract 长期不一致
```

重要 API Contract 必须至少有一层真实 Contract / Integration 验证。

## 24. 构建与质量 Gate

推荐最少包含：

```text
Type Check
Lint
Unit / Component Test
Production Build
E2E（关键范围）
```

Gate 必须独立、可重复执行，失败必须返回非零退出状态。

## 25. 依赖管理

新增依赖必须回答：

1. 为什么需要？
2. 是否已有等价能力？
3. Bundle Size 影响？
4. License？
5. 安全维护状态？
6. 是否引入重复能力？

禁止为了一个简单工具函数引入大型依赖。

## 26. 环境配置

区分：

```text
Build-time configuration
Runtime configuration
Secret
Public configuration
```

前端打包进入浏览器的变量默认视为公开信息，不能存放 Secret。

## 27. 日志与可观测性

前端日志应服务于诊断，而不是输出所有业务数据。

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
完整敏感业务 payload
```

## 28. 代码与注释

注释解释：

```text
为什么这样做
有什么约束
为什么不能用更简单方案
```

不要解释显而易见的代码。

复杂组件必须在顶部或相邻文档说明：职责、边界、关键依赖。

## 29. Refactor 规则

重构必须完成：

```text
新结构
 ↓
全部引用迁移
 ↓
测试迁移
 ↓
旧实现删除
 ↓
全仓搜索旧路径
 ↓
重复实现检查
 ↓
测试 Gate
```

禁止长期保留：

```text
legacy/
old/
compat/
adapter-only forwarding
```

来掩盖迁移未完成。

## 30. Git 与 Commit

推荐：

```text
feat(frontend): ...
fix(frontend): ...
refactor(frontend): ...
test(frontend): ...
chore(frontend): ...
```

一个 Commit 应尽量对应一个可解释的工程变化。

不要把无关格式化、依赖升级、业务修改混入同一个 Commit。

## 31. 新 Feature 标准流程

```text
① 阅读项目 DEVELOPMENT.md
② 同步最新代码
③ 搜索已有 Feature / Component / API / Store
④ 确认 Backend Contract
⑤ 定义 Feature 边界
⑥ 定义 Type / DTO
⑦ 实现 API Client / Service
⑧ 实现 Domain / Composable
⑨ 实现 Component / View
⑩ Unit / Component Test
⑪ Integration Test（需要时）
⑫ Production Build
⑬ E2E（关键路径需要时）
⑭ 更新文档 / Status / Acceptance
⑮ Commit
```

## 32. Definition of Done

前端功能只有同时满足适用项才算完成：

```text
[ ] Feature boundary clear
[ ] Contract aligned
[ ] Type complete
[ ] Permission considered
[ ] Loading / Empty / Error handled
[ ] Accessibility considered
[ ] Unit / Component tests
[ ] Production build
[ ] E2E for critical path
[ ] No duplicate implementation
[ ] No secret leakage
[ ] Documentation updated
[ ] Git change traceable
```

## 33. 禁止事项

```text
❌ any 驱动的类型系统
❌ View 内堆积业务逻辑
❌ 一个万能 Store
❌ 一个万能 utils.ts
❌ 页面各自创建 HTTP Client
❌ 前端权限代替后端权限
❌ 非幂等 API 无脑 retry
❌ Mock 长期脱离真实 Contract
❌ 用兼容层掩盖重构未完成
❌ 未验证的“性能优化”
❌ Secret / Token 进入源码或日志
❌ 只验证成功路径
❌ 只写代码不更新 Contract / 文档
```

## 34. 与项目治理文档的关系

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

本文件解决“Vue + TypeScript 项目应该如何工程化”；具体项目文档负责补充具体 UI 框架、目录、命令、部署、CI 和测试环境。
