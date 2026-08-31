# UI-03 Dashboard 页面迁移记录

## 1. 目标

将平台 Dashboard 从页面私有视觉实现迁移到 UI-03 公共页面模式，保持现有业务行为、API Contract 和路由不变。

## 2. 迁移范围

- 页面头部：`PageHeader`
- 核心指标：`MetricCard`
- 内容容器：`SurfaceCard`
- 页面布局：Design Tokens + 响应式断点
- 最近执行、常用入口、失败运行提醒保持原有功能

## 3. 设计决策

### 3.1 PageHeader

原有 Dashboard 自定义 hero/header 被公共 `PageHeader` 替代，统一标题层级、描述和右侧操作区域。公共组件已经提供 700px 以下的纵向布局，因此页面不再维护重复的 Header 响应式逻辑。

### 3.2 MetricCard

原有 `el-card` 指标卡迁移至 `MetricCard`，统一指标数字、说明和辅助趋势信息的视觉层级。现有指标业务含义不变。

### 3.3 SurfaceCard

“最近执行”和“常用入口”统一为 `SurfaceCard`，复用统一的 border、radius、surface、header/body spacing。

### 3.4 Token 化

迁移后的页面私有样式优先引用 `--ui-*` Design Tokens，避免继续增加页面级颜色、间距、阴影硬编码。

### 3.5 响应式

保留 Dashboard 的信息结构，在 1100px 以下将两栏工作区改为单栏；700px 以下指标改为两列；420px 以下改为单列。核心内容不隐藏、不改变 API 数据结构。

## 4. 兼容性

- Vue 3 + TypeScript
- Element Plus
- 现有 `listAgents`、`listTools`、`runtimeApi.executions` API 不变
- 既有 `/runtime` 快速入口保持不变
- 未引入新的后端 Contract

## 5. 测试

新增 `tests/views/DashboardUI03.test.ts`，覆盖：

1. PageHeader / MetricCard / SurfaceCard 公共组件接入；
2. 五个核心指标卡保持存在；
3. Empty 状态；
4. 智能体、工具、运行记录等快速入口；
5. 页面核心中文文案。

本次远端开发没有执行本地 Node/Vitest/build，因此测试状态只能记录为“待本地执行”，不得标记为通过。

## 6. 本地验证

```powershell
cd frontend
npm test -- tests/views/DashboardUI03.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

视觉验收：1440 / 1280 / 1024 / 768 / 390。

## 7. 后续

Dashboard 本轮只完成 UI-03 公共模式迁移，不提前混入 UI-04 状态体系、UI-05 Dialog/Form 专项或 UI-06 全量 Token 清理。后续任务继续采用单页面原子迁移。
