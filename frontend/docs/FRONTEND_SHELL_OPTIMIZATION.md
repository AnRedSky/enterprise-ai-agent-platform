# 前端平台壳层与页面体验优化

## 1. 目标

本次交付以“形成真实可用的系统”为目标，不新增尚未冻结的后端业务 Contract。重点解决现有前端页面之间缺少统一工作台体验的问题：登录后各业务页面使用同一导航、顶部上下文、用户会话和视觉规范，并保持现有 API 与领域页面功能不变。

## 2. 基线与约束

- 基线：远程 `main`，提交 `edadbb1cfd3f61344d923baedd828a4540f53367`。
- 技术栈：Vue 3 + TypeScript + Vite + Element Plus + Pinia。
- 后端 Contract 是唯一业务契约；本次不虚构 Webhook Delivery 等尚未冻结的接口。
- 前端测试实现继续位于 `frontend/tests/`，不把测试逻辑放入生产目录。
- 所有实现、说明和测试必须可重复执行；开发完成后执行 Frontend Gate，并按范围执行浏览器 E2E。

## 3. 当前问题

此前 `App.vue` 只渲染 `router-view`，各页面虽然已有业务 Workbench，但缺少统一的产品级壳层。路由已经覆盖 Dashboard、Agent、Tool、Knowledge、Workflow、Organization、Runtime、Audit 等核心能力，但用户需要通过页面自身提供入口完成切换，移动端和桌面端也没有统一的布局约束。

## 4. 设计决策

### 4.1 AppShell 作为登录后的统一入口

`App.vue` 根据路由 `meta.public` 判断是否使用平台壳层：登录页保持独立，其他页面统一进入 `AppShell`。这样不会污染认证页面，也不会改变现有业务路由。

### 4.2 导航直接复用现有路由

侧边栏只使用已经存在的业务路由，不新增假页面。工作流采用二级菜单展示“工作流编排”和“触发器”，组织详情与模型 Provider 保留为业务内页入口，避免在全局导航中生成无效的动态 `:id` URL。

### 4.3 会话信息直接复用现有 Auth API

用户 ID、角色、退出登录均复用 `src/api/auth.ts` 的既有会话存储能力。退出操作清理当前会话并回到登录页，不创建第二套用户状态。

### 4.4 视觉规范集中化

新增 `src/styles/global.css`，统一页面背景、字体、卡片、表格、表单控件、间距、侧边栏、顶部导航和响应式断点。领域 Workbench 仍保留自己的业务样式，避免一次性大规模重写已经存在且经过测试的业务组件。

### 4.5 响应式策略

桌面端使用 248px 导航栏，支持折叠为 72px；900px 以下自动进入紧凑导航模式；600px 以下进一步压缩顶部操作区和页面边距。核心目标是保证业务页面在常见笔记本和窄屏环境下仍可操作。

## 5. 实现清单

| 文件 | 变更 | 目的 |
|---|---|---|
| `src/App.vue` | 重构 | 登录页与业务壳层分流 |
| `src/components/AppShell.vue` | 新增 | 统一导航、顶部栏、用户菜单、页面过渡 |
| `src/main.ts` | 精简并引入全局样式 | 统一应用初始化 |
| `src/styles/global.css` | 新增 | 产品级全局视觉与响应式规范 |
| `tests/views/AppShell.test.ts` | 新增 | 验证导航、会话展示和路由切换 |
| `docs/FRONTEND_SHELL_OPTIMIZATION.md` | 新增 | 记录设计决策与实现边界 |

## 6. 验收策略

必须在 `frontend` 目录执行：

```powershell
npm test
npm run build
npm run test:gate
```

其中 `test:gate` 只编排 Frontend Test + Production Build，不调用 Backend、数据库或 Real API，符合项目 Gate 隔离规则。

浏览器验证应覆盖：登录 → 工作台 → Agent → Tool → 知识库 → 工作流/触发器 → 组织管理 → Runtime → 审计日志；同时验证侧边栏折叠、刷新、退出登录和窄屏布局。

## 7. 已知边界

本次不实现 2.9-D Webhook Delivery UI，因为后端 Reliable Delivery 的最终并发、幂等、租约、重试和 HTTP Contract 尚未冻结。前端应在后端 Contract 完成真实验收后再进入对应 API Types → Vitest → UI → Real API → E2E 顺序。
