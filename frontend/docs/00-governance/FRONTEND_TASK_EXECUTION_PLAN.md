# 前端长期任务执行计划

> 本文件是前端持续开发的任务执行台账，不替代项目阶段文档。状态必须基于远端 `main`、当前前端代码和本地实际测试结果更新。

## 1. 当前基线

- 最新远端 `main`：`2fccc9ddee10579e8dfcc6e684164e140b7356bc`（2026-08-31，Runtime Audit Query 路由修复）。
- 当前 `frontend` 已同步到该 `main`，本轮 UI 整改基于稳定后端 Contract，不新增业务 Contract。
- 当前主线暂缓新增业务功能，优先解决系统 UI 无法达到企业级使用标准的问题。
- 前端开发准则要求保持现有企业级信息架构，采用渐进增强；公共视觉规则应统一收敛到 Design Tokens 和公共组件。

## 2. 当前主线：UI-01 + UI-02

状态：**进行中：首轮基础系统整改已实现。**

### UI-01：Design System Foundation

已实现：

- `src/styles/tokens.css`：颜色、文字、间距、圆角、阴影、布局和控件尺寸 Token；
- `src/styles/reset.css`：基础 reset、焦点可见性和 reduced-motion；
- `src/styles/typography.css`：统一字体与文本层级；
- `src/styles/components.css`：Element Plus 全局控件视觉基线；
- `src/styles/global.css`：应用布局变量、页面容器和响应式规则。

### UI-02：Application Shell

已实现：

- 侧边栏品牌、工作区、导航分组、系统状态统一视觉；
- 顶部上下文栏、搜索、帮助、通知、环境和用户菜单统一视觉；
- Shell 视觉参数统一引用 Design Tokens；
- 保持既有业务路由和信息架构不变；
- 700px 以下采用紧凑导航模式；
- 增强键盘焦点和 reduced-motion 支持。

## 3. UI 整改后续队列

### P0：系统 UI 全面整改

1. UI-03：Page Header / Toolbar / Metric / Card / Table 公共模式统一；
2. UI-04：Loading / Empty / Error / Permission / Success 状态统一；
3. UI-05：表单、Dialog、Drawer、确认操作和危险操作视觉/交互统一；
4. UI-06：核心页面逐页迁移至 Design Tokens，清理散落硬编码样式；
5. UI-07：1440 / 1280 / 1024 / 768 / 390 响应式视觉验收；
6. UI-08：核心页面可访问性、交互密度和视觉一致性专项整改。

### 业务功能

新增业务功能暂缓。UI-01 至 UI-08 完成前，不进入新的业务领域开发；现有业务仅允许进行 UI 兼容整改和必要缺陷修复。

## 4. 固定执行流程

```text
同步远端 main
    ↓
确认 Backend Contract / Tests / Acceptance
    ↓
检索现有 UI / Components / Styles / Tests / Docs
    ↓
确定一个 UI 原子整改单元
    ↓
实现源码 + 测试 + 必要文档
    ↓
targeted test → npm test → npm run build → npm run test:gate
    ↓
必要时 Real API / Browser E2E
    ↓
同步 frontend/docs
    ↓
一个原子提交
```

## 5. 本轮验证状态

本轮 UI-01 + UI-02 已通过 GitHub 远端源码修改完成；当前执行环境不能直接运行用户本地 Node/Vitest/build，因此不能将这些测试记录为“通过”。

用户本地应执行：

```powershell
cd frontend
npm test
npm run build
npm run test:gate
npm run test:final
```

视觉验收至少检查 1440 / 1280 / 1024 / 768 / 390 五档 viewport，并重点验证导航、页面容器、表格、表单、Dialog、Loading、Empty、Error 和 Permission 状态。

测试数据必须由既有脚本自动生成；测试流程不得自动启动/停止服务，也不得要求手动填写测试信息。

## 6. 完成定义

任务只有同时满足代码实现、视觉一致性、响应式、可访问性、targeted/full Vitest、build、test gate、必要 Real API/E2E、文档同步和原子提交等条件，才能标记 `已完成`。

没有实际执行证据不得写成“通过”。
