# Vue + TypeScript 模块入口与 `index.vue` 通用准则

> 本规范补充 `FRONTEND_VUE_TYPESCRIPT_GUIDELINES.md`，用于统一页面模块、Layout 模块、Feature 模块的入口约定。
>
> 核心原则：**目录表示模块，`index.vue` 表示模块 UI 入口，模块内部实现保持语义化命名。**

## 1. 适用范围

本规范适用于：

- Layout 模块
- View / Page 模块
- Feature 模块
- Workspace / 场景模块
- 需要作为 Vue Router 页面入口的模块

不要求所有 `.vue` 组件都命名为 `index.vue`。

---

## 2. 统一入口规则

目录级 UI 模块统一使用：

```text
<module>/
└── index.vue
```

推荐：

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
    ├── components/
    ├── composables/
    ├── stores/
    ├── api/
    └── types/
```

`index.vue` 是模块的 **UI Composition Root**，负责组合模块内部能力，而不是承载全部实现。

---

## 3. Layout 入口

Layout 使用 `index.vue` 作为布局入口：

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

职责：

```text
页面框架
Header
Sidebar
Navigation
Breadcrumb
Tabs
Content Container
Footer
Responsive Layout
RouterView
```

禁止 Layout 直接承载具体业务 Feature 规则。

---

## 4. View 入口

页面模块统一：

```text
views/<domain>/index.vue
```

例如：

```text
views/users/
├── index.vue
├── components/
├── composables/
├── api/
└── types/
```

View 负责：

```text
页面级组合
路由参数接入
页面级交互编排
页面状态展示
Feature 组合
```

View 不应直接成为 API、业务规则、复杂状态和 UI 的全部承载点。

---

## 5. Feature 入口

当业务达到 Feature 化条件：

```text
features/<domain>/
├── index.vue
├── components/
├── composables/
├── stores/
├── api/
├── types/
├── constants/
└── utils/
```

`index.vue` 负责组合 Feature 的公开 UI 能力。

Feature 的非 UI Public API 仍使用：

```text
index.ts
```

因此一个 Feature 可以同时具有：

```text
index.vue = UI Entry
index.ts   = Programmatic Public API
```

两者职责不同，不应混为一谈。

---

## 6. `index.vue` 的职责边界

`index.vue` 推荐负责：

```text
Layout / Template Composition
Props 接入
Route 参数接入
Feature Component 组合
Composable 编排
页面级状态展示
页面级事件处理
```

不推荐负责：

```text
底层 HTTP 实现
大型业务规则
复杂数据转换
跨 Feature 全局状态
WebSocket 生命周期
复杂轮询机制
大量纯函数
```

复杂逻辑应下沉到：

```text
components/
composables/
stores/
api/
services/
utils/
```

---

## 7. 内部组件命名

只有目录级模块入口使用 `index.vue`。

内部组件必须保持语义化命名：

```text
components/
├── UserTable.vue
├── UserForm.vue
├── UserDetail.vue
└── UserToolbar.vue
```

禁止：

```text
components/
├── index.vue
├── index.vue
└── index.vue
```

原因：

- IDE 搜索困难
- Debug 堆栈难以识别
- Code Review 可读性下降
- 组件语义丢失
- 大型项目维护成本增加

---

## 8. Router 入口规范

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

这样可以形成：

```text
Router
  ↓
Layout/index.vue
  ↓
View/index.vue
  ↓
Feature/index.vue
```

---

## 9. 模块渐进式扩展

模块可以从最小结构开始：

```text
users/
└── index.vue
```

随着复杂度增加：

```text
users/
├── index.vue
├── components/
└── composables/
```

继续增长：

```text
users/
├── index.vue
├── components/
├── composables/
├── stores/
├── api/
└── types/
```

入口始终保持：

```text
users/index.vue
```

这使模块能够在不改变路由和外部引用的情况下内部演进。

---

## 10. View 与 Feature 的关系

两者都可以使用 `index.vue`，但语义不同：

```text
views/users/index.vue
= 页面入口

features/users/index.vue
= 业务能力 UI 入口
```

推荐关系：

```text
Router
 ↓
Layout/index.vue
 ↓
View/index.vue
 ↓
Feature/index.vue
```

简单项目不必强制同时存在 View 和 Feature。

如果页面本身就是一个独立业务模块，可以直接使用：

```text
views/users/index.vue
```

随着业务复杂度增长，再拆分 Feature。

---

## 11. 模块 Public API

UI 模块的外部入口：

```text
index.vue
```

程序化能力入口：

```text
index.ts
```

例如：

```text
features/workflow/
├── index.vue
├── index.ts
├── components/
├── composables/
└── api/
```

外部模块禁止依赖：

```text
features/workflow/components/internal/*
features/workflow/stores/private/*
```

优先依赖模块公开入口。

---

## 12. 模块依赖原则

推荐：

```text
Router
 ↓
Layout
 ↓
View
 ↓
Feature
 ↓
Shared / Services
 ↓
Infrastructure
```

禁止：

```text
Layout → Feature Internal
Shared → View
Utils → Feature
Service → View
Feature A → Feature B Internal
```

如果模块需要访问另一个模块，应通过公开接口或明确 Contract。

---

## 13. 何时创建模块目录

满足以下任一条件，可以创建目录模块：

```text
存在独立页面
存在独立业务边界
存在多个相关组件
存在独立状态
存在独立 API
存在独立路由
```

只有一个简单组件时，不需要为了规范创建完整模块目录。

---

## 14. 何时拆分 `index.vue`

当 `index.vue` 出现以下情况时，应考虑拆分：

```text
多个复杂区域
大量模板
复杂业务逻辑
多个独立交互流程
多个可复用组件
多个异步流程
状态明显超过页面编排职责
```

推荐：

```text
index.vue
    ↓
components/
    ↓
composables/
    ↓
stores/
    ↓
api/
```

而不是继续增加 `index.vue` 的代码规模。

---

## 15. 禁止规则

禁止：

1. 所有 `.vue` 文件都命名为 `index.vue`。
2. 在 `index.vue` 中直接堆积所有业务代码。
3. 通过 `index.vue` 绕过模块边界访问其他模块内部实现。
4. 为了目录完整性提前创建大量空模块。
5. Layout 中硬编码具体业务页面逻辑。
6. View 中实现基础 UI 组件。
7. 用 `index.vue` 隐藏组件本身的语义。

---

## 16. 最终统一模型

```text
src/
├── layouts/
│   └── <layout>/
│       ├── index.vue              # Layout UI Entry
│       └── components/
│
├── views/
│   └── <page>/
│       ├── index.vue              # Page UI Entry
│       └── components/
│
└── features/
    └── <domain>/
        ├── index.vue              # Feature UI Entry
        ├── index.ts               # Programmatic Public API
        ├── components/
        ├── composables/
        ├── stores/
        ├── api/
        ├── types/
        └── utils/
```

最终形成：

```text
目录 = 模块边界
index.vue = UI 模块入口
index.ts = 程序化 Public API
语义化文件名 = 内部实现
```

这套约定适合从小型 Vue 项目渐进式演进到大型企业级前端项目，无需因为采用模块化规范而一次性重构已有代码。
