# 前端长期任务执行计划

> UI-03 持续开发台账。每轮按单一核心页面原子迁移执行。

## 当前基线
- 最新 `main`：`f0cc9081f2756bf9c23d64d034b2260cd8a2d47b`。
- `frontend` 已通过 merge commit 同步最新 `main`。
- 新业务功能暂缓，优先完成 UI-03 至 UI-08。

## UI-03 公共页面视觉体系

状态：**进行中：已完成工具管理、平台工作台两个核心页面迁移。**

公共模式：`PageHeader`、`PageToolbar`、`MetricCard`、`SurfaceCard`。

已迁移：
- `views/tools/components/ToolWorkbench.vue`
- `views/dashboard/components/DashboardOverview.vue`

测试：
- `tests/views/Tools.test.ts`
- `tests/views/DashboardUI03.test.ts`

设计记录：
- `docs/01-design/UI_03_DASHBOARD_MIGRATION.md`

固定流程：

```text
一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交
```

下一轮继续只选择一个核心页面，不进行全量页面批量重构。

## 后续队列
1. UI-03：继续核心页面公共模式迁移；
2. UI-04：Loading / Empty / Error / Permission / Success；
3. UI-05：Form / Dialog / Drawer / Confirm；
4. UI-06：核心页面 Token 清理；
5. UI-07：1440 / 1280 / 1024 / 768 / 390 响应式验收；
6. UI-08：可访问性、交互密度和视觉一致性。

## 本轮测试状态

当前执行环境不能运行用户本地 Node/Vitest/build，因此不得记录为“通过”。

```powershell
cd frontend
npm test -- tests/views/DashboardUI03.test.ts
npm test -- tests/views/Tools.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

没有实际执行证据不得标记任务完成。