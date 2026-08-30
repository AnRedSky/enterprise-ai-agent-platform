# 前端长期任务执行计划

> 本文件是前端持续开发的任务执行台账，不替代项目阶段文档。状态必须基于远端 `main`、当前前端代码和本地实际测试结果更新。

## 1. 当前基线

- 最新远端 `main`：`b8acde920af3ade85291d44b578bfd32a36ddb6a`（2026-08-30，Runtime Audit tenant boundary regression test）。
- 本轮已通过 PR #56 将最新 `main` 合并到 `frontend`，合并提交为 `03c628c18a313c8fddf37ce9448c13b08cf33dc6`。
- 后端最新 Audit Contract 已提供 tenant-scoped、1~1000 bounded、稳定排序的基础查询入口；前端继续复用现有 `/runtime/audit-logs` API，不新增平行 API。
- 用户本地此前存在 Node 依赖目录不完整的问题：`node_modules/.bin/vite.cmd` 不存在，`npm ci` 因 Windows `@esbuild/win32-x64/esbuild.exe` 文件锁返回 EPERM，故本地验证仍需重新安装依赖后执行。

## 2. 当前主线：P1.1 / P1.3 / P1 稳定性

### P1.3：Runtime ↔ Workflow 双向深链

状态：**进行中**。

代码已实现真实 `workflow_id` 上下文双向导航；本地 targeted/full Vitest、build、test gate、Real API 与 Browser E2E 尚未取得实际证据。

### FE-P1-04：Element Plus 未解析组件/指令警告治理

状态：**进行中**。

生产入口已注册官方 `v-loading`，并增加启动层回归测试；本地验收未完成。

### FE-P1-05：Audit 可观测性体验加固

状态：**进行中**。

本轮实际实现：

1. Audit 状态筛选使用有限后端状态值选择器；
2. Empty 状态提供“查看全部记录”恢复动作；
3. Error 状态提供重新加载且不暴露原始异常正文；
4. Audit 的真实 `execution_id` 可直接深链 Runtime；完整 ID 保留在 query，展示层仅紧凑化；
5. 表格和筛选区增加窄屏响应式适配；
6. 新增 AuditLog targeted Vitest；
7. 新增 `npm run test:local:full` 统一本地回归入口；脚本只做依赖/服务 readiness 检查，不自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis，也不要求手工输入测试数据。

## 3. 长期任务队列

### P0：核心业务闭环

| ID | 领域 | 目标 | 状态 | 验收 |
|---|---|---|---|---|
| FE-P0-01 | Agent | 创建 → Version → Publish → Runtime → Trace/Audit 闭环 | 进行中 | View + API + Real 联调 |
| FE-P0-02 | Workflow | 编辑 → 校验 → 发布 → Execution → Trace | 进行中 | View + API + E2E |
| FE-P0-03 | Runtime | Execution → Event → Trace → Audit 统一详情链路 | 进行中 | View + API + E2E |
| FE-P0-04 | Knowledge | 知识资产 → 检索 → Agent 关联 → Runtime 验证 | 待实施 | View + API |
| FE-P0-05 | Tool | 工具配置 → Agent 关联 → Runtime 调用结果 | 待实施 | View + API |
| FE-P0-06 | Organization | 组织 → 成员 → 权限 → 资源边界 | 待实施 | View + API + E2E |
| FE-P0-07 | Model Provider | Provider/Model 配置与 Agent 使用关系 | 待实施 | View + API |
| FE-P0-08 | Audit | 跨领域操作证据查询与详情 | 进行中 | View + API + E2E |
| FE-P0-09 | Integration | Event → Delivery → Audit → Replay → Dead Letter | 待实施 | View + Real API |

### P1：稳定性与企业级体验

- FE-P1-01：统一 Loading / Empty / Error / Success / Permission 状态。
- FE-P1-02：统一错误分类与用户提示隔离。
- FE-P1-03：统一中文状态映射，未知值安全回退。
- FE-P1-04：清理 Element Plus 未解析组件警告（进行中）。
- FE-P1-05：统一公共模式，并完成本轮 Audit 页面渐进增强（进行中）。
- FE-P1-06：建立 1440 / 1280 / 1024 / 768 / 390 响应式验收矩阵。
- FE-P1-07：补充核心页面 Playwright 用户旅程。
- FE-P1-08：完成 P1.1 Runtime / Agent / Workflow 深度交互与可观测性工作台。

### P2：2.10-I 后端稳定后再实施

- Provider Registry / Health；
- Alert Rule 与 firing/recovery 生命周期；
- Notification Routing / Provider fallback；
- Notification SLO / Route Metrics；
- Runtime Alert Scheduler 运维视图；
- Prometheus / OpenTelemetry 配置与观测状态。

### P3：平台化长期能力

- Design System 与 Design Token；
- 全局搜索与快捷命令；
- 页面级权限矩阵与通知中心；
- Dashboard 趋势与运营驾驶舱；
- 无障碍与响应式深化；
- 性能预算、资源优化和可观测前端；
- 主题 / 国际化 / 大屏。

## 4. 固定执行流程

```text
同步远端 main
    ↓
确认 Backend Contract / Tests / Acceptance
    ↓
检索现有 API / Types / View / Components / Tests / Docs
    ↓
确定最小业务切片
    ↓
API Types → View / Component → Vitest
    ↓
targeted test → npm test → npm run build → npm run test:gate
    ↓
必要时 Real API / Browser E2E
    ↓
同步 frontend/docs / 项目状态
    ↓
一个原子提交
```

## 5. 本地全面测试

统一入口：

```powershell
cd frontend
npm ci
npm run test:local:full
```

脚本内部依次执行 targeted AuditLog、全量 Vitest、production build、frontend regression gate，并检查已有 Backend API 与 Frontend E2E 服务是否可访问；服务不存在时 E2E 标记 `NOT EXECUTED` 并停止，不自动启动/停止任何后端基础设施。

也可以按标准流程分别执行：

```powershell
npm test -- tests/views/AuditLog.test.ts
npm test
npm run build
npm run test:gate
npm run test:e2e
```

没有实际执行证据，不得把代码检查结果写成通过。

## 6. 完成定义

任务只有同时满足 Backend Contract、类型、用户链路、状态完整性、安全边界、targeted/full Vitest、build、test gate、必要 Real API/E2E、文档同步和原子提交等条件，才能标记 `已完成`。

## 7. 状态规则

只允许：`待实施`、`进行中`、`阻塞`、`已完成`。没有实际执行证据不得写成“通过”。
