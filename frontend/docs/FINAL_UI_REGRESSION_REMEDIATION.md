# 前端最终回归失败整改记录

> 基线：`main` @ `98c3a055c1eb5043eacb2498fd1eb2036799c8ed`
> 日期：2026-08-30
> 范围：Final UI Release Gate 回归问题整改，不扩展 P2.10-I。

## 1. 本地反馈基线

本次本地 `frontend/npm run test:final` 实际结果为：

- Test Files：`11 failed | 17 passed (28)`
- Tests：`22 failed | 107 passed (129)`
- Duration：约 `62.54s`
- Final Release Gate：阻塞

失败集中在 Workflow Trigger、Runtime、Workflow、Dashboard、Agents、Organizations、Model Providers 等视图。

## 2. 本次确认的前端 Contract 回归

### Workflow Trigger

发现治理页面仍以 `saveTrigger()` 作为表单实现入口，但现有前端单元测试和页面内部测试契约以 `createTrigger()` 作为创建入口。该差异会直接导致 `vm.createTrigger is not a function`，并阻断 Scheduled / Manual / Config 校验测试。

本次修复：

- 保留 `saveTrigger()` 作为统一保存实现；
- 增加正式的 `createTrigger()` 页面操作入口并委托到 `saveTrigger()`；
- 表单提交统一经过 `createTrigger()`；
- 增加明确的 Scheduled Trigger Contract 提示：`timezone + interval_seconds`；
- Scheduler 状态继续只从后端持久化状态接口读取，不在前端推断。

## 3. 未宣称已通过的项目

本次修改后尚未在当前会话中执行用户本地 Windows 环境的 `npm run test:final`，因此不得将本提交标记为最终 Gate PASS。

用户本地环境必须重新执行：

```powershell
cd frontend
npm run test:phase:p2
npm run test:phase:p3
npm run test:phase:p4
npm run test:final
```

如果需要针对单个失败视图缩短日志，应优先执行：

```powershell
npx vitest run tests/views/WorkflowTriggers.test.ts
npx vitest run tests/views/Runtime.test.ts
npx vitest run tests/views/Workflows.test.ts
npx vitest run tests/views/Agents.test.ts
npx vitest run tests/views/Organizations.test.ts tests/views/OrganizationDetail.test.ts
npx vitest run tests/views/ModelProviders.test.ts
npx vitest run tests/views/Dashboard.test.ts
```

## 4. 手动验收边界

自动化回归恢复通过后，再执行 production build 与真实前后端联调。Real API、浏览器 E2E 和人工视觉验收仍保持独立 Gate，不在 Frontend Vitest 中伪造服务状态。

## 5. 长期优化计划

1. 为每个主领域维护 phase-level targeted Gate，避免开发期默认执行全量回归。
2. 将页面状态机测试拆分为 API Contract、生命周期操作、错误状态、权限状态四类。
3. 为 Runtime 建立 Trigger → Execution → Trace → Audit 的稳定可观测断言。
4. 为 Scheduler / Webhook 建立真实入口到 Runtime 的导航验收。
5. 完成所有视图的 Loading / Empty / Error / Disabled 状态统一。
6. 最终 Gate 仅在主线实现冻结后执行，避免开发中反复产生超长日志。
