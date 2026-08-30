# Frontend Full Vitest Regression Remediation — 2026-08-30

## 1. 本次基线

`main` 与 `frontend` 当前已同步，最新共同提交为 `9f6fe5c8928f2bb501adb6a85eb3f79dabbaade3`。

本地 `npm run test:local:full` 已完成依赖、目标测试及全量 Vitest 阶段，但全量 Vitest 首次执行为 `22 passed / 9 failed`。

## 2. 失败分类

### 测试语法阻断

`tests/views/RuntimeWorkspaceTabs.test.ts` 中 `el-button` stub 的 template 使用双引号嵌套 `$emit("click")`，导致 esbuild 在 transform 阶段报 `Expected "}" but found "$emit"`。修复为模板字符串，避免 Vue template 属性与 JavaScript 字符串的引号冲突。

### UI 文本契约漂移

若页面已经完成中文 UI 治理，测试不得继续断言旧英文或旧领域术语：

- `delivered` → `已送达`
- `Idempotency Key` → `幂等标识`
- `暂无 Destination` → `暂无投递目标`
- `新建 Subscription` → `新建事件订阅`
- `请先创建至少一个 Destination` → `请先创建至少一个投递目标`

Agent 调试测试改为验证真实调试上下文打开后的 `调试：<智能体>` 标题，而不是依赖表格内部按钮 stub 的渲染细节。

### 异步测试竞态

`OperationsConsole` 测试原先只等待页面标题出现即读取 SLO 指标；页面标题属于同步渲染，而 overview 数据通过异步 API 加载。测试改为等待真实异步结果 `99.50%` 后再验证指标与 API 调用。

Workflow 创建/运行测试同样在创建与运行动作之间等待真实 `execution.id/status` 状态，避免测试依赖 Promise 微任务调度顺序。

### 第三方组件测试警告

`AppShell` 测试补充 `el-aside` layout stub。该问题原本不会导致断言失败，但会产生 `Failed to resolve component: el-aside` 噪声，降低回归结果可读性。

### 关系字段断言

Runtime Retry/Resume 测试优先验证后端真实关系字段：`retry_of_execution_id`、`resume_of_execution_id`、`resume_checkpoint_sequence`，避免将表格/描述组件的文本布局作为关系 Contract 的唯一事实来源。

### 错误文案标点

Organization Detail 当前统一使用 `组织详情加载失败，请稍后重试。`，测试同步当前正式 UI 文案。

## 3. 设计原则

1. 不为了让测试通过而恢复旧英文 UI。
2. 不在前端复制后端状态机或业务计算。
3. 测试优先验证 API 参数、真实 ID、后端字段与用户可见状态映射。
4. UI 文本断言只验证正式用户可见文案，不把历史英文术语当作 Contract。
5. 异步页面必须等待业务数据稳定状态，而不是等待任意同步标题。
6. 测试 stub 应覆盖必要的 Element Plus 结构，但不得模拟业务逻辑。

## 4. 验证顺序

```powershell
npm test -- tests/views/RuntimeWorkspaceTabs.test.ts tests/views/OperationsConsole.test.ts tests/views/Integrations.test.ts tests/views/IntegrationEventConsole.test.ts tests/views/Agents.test.ts tests/views/OrganizationDetail.test.ts tests/views/Organizations.test.ts tests/views/Runtime.test.ts tests/views/Workflows.test.ts
npm test
npm run build
npm run test:gate
```

本次修改没有自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis，也没有引入手工测试数据输入。完整回归在本地服务未就绪时继续遵循“只检查、不自动启动”的既定边界。

## 5. 当前验收状态

本文件只记录修复内容；在开发者重新执行上述命令之前，不将全量 Vitest、Build、Gate 或 E2E 标记为通过。