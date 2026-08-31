# 前端长期任务执行计划

> 本文件是前端持续开发的任务执行台账，不替代项目阶段文档。状态必须基于远端 `main`、当前前端代码和本地实际测试结果更新。

## 1. 当前基线

- 最新远端 `main`：`f0cc9081f2756bf9c23d64d034b2260cd8a2d47b`（2026-08-31，Runtime Audit Query 后续主线合并）。
- 当前 `frontend` 已完成与该 `main` 的同步；UI-03 页面迁移继续基于稳定 Backend Contract，不新增业务 Contract。
- 当前主线暂缓新增业务功能，优先解决系统 UI 无法达到企业级使用标准的问题。
- 前端开发准则要求保持现有企业级信息架构，采用渐进增强；公共视觉规则统一收敛到 Design Tokens 和公共组件。

## 2. UI 整改主线

### UI-01：Design System Foundation

状态：**完成首轮基础实现**。

### UI-02：Application Shell

状态：**完成首轮基础实现**。

### UI-03：公共页面视觉体系

状态：**进行中：公共模式组件已建立，并已完成工具管理、平台工作台两个核心页面迁移。**

已实现：

- `src/components/ui/PageHeader.vue`：页面唯一主标题、描述、主操作；
- `src/components/ui/PageToolbar.vue`：列表筛选、搜索、批量操作、视图操作；
- `src/components/ui/MetricCard.vue`：关键指标、趋势和辅助信息；
- `src/components/ui/SurfaceCard.vue`：统一内容容器、Header、Body 和局部操作；
- `views/tools/components/ToolWorkbench.vue`：迁移至公共页面模式；
- `views/dashboard/components/DashboardOverview.vue`：迁移至 `PageHeader` + `MetricCard` + `SurfaceCard`，保留指标、运行记录、快速入口和异常提醒；
- `tests/views/Tools.test.ts`、`tests/views/DashboardUI03.test.ts`：覆盖核心迁移结构和关键空状态/入口；
- `docs/01-design/UI_03_DASHBOARD_MIGRATION.md`：记录 Dashboard 迁移决策、兼容性和验证要求。

本阶段坚持“一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交”，不修改业务 API 和领域逻辑。

### 下一迁移候选

继续从核心业务页面中选择单一页面进行迁移。优先选择访问频率高、结构稳定、公共组件复用收益高且不需要新的 Backend Contract 的页面。当前不进行全量页面批量重构。

## 3. UI 整改后续队列

### P0：系统 UI 全面整改

1. UI-03：公共页面模式统一，并将核心页面逐步迁移至公共组件；
2. UI-04：Loading / Empty / Error / Permission / Success 状态统一；
3. UI-05：表单、Dialog、Drawer、确认操作和危险操作视觉/交互统一；
4. UI-06：核心页面逐页迁移至 Design Tokens，清理散落硬编码样式；
5. UI-07：1440 / 1280 / 1024 / 768 / 390 响应式视觉验收；
6. UI-08：核心页面可访问性、交互密度和视觉一致性专项整改。

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

Dashboard UI-03 迁移已完成远端源码、测试和文档；当前执行环境不能直接运行用户本地 Node/Vitest/build，因此不能将测试记录为“通过”。

本地执行：

```powershell
cd frontend
npm test -- tests/views/DashboardUI03.test.ts
npm test -- tests/views/Tools.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

视觉验收至少检查 1440 / 1280 / 1024 / 768 / 390 五档 viewport。测试数据继续由既有脚本自动生成，不自动启动/停止服务，不要求手动填写测试信息。

## 6. 完成定义

只有同时满足代码实现、视觉一致性、响应式、可访问性、targeted/full Vitest、build、test gate、必要 Real API/E2E、文档同步和原子提交等条件，才能标记 `已完成`。没有实际执行证据不得写成“通过”。
