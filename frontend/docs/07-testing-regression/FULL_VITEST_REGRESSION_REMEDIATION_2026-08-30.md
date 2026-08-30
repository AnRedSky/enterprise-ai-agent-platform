# Frontend Full Vitest Regression Remediation — 2026-08-30

## 1. 本次基线

`main` 与 `frontend` 当前已同步，最新共同提交为 `4e31f477e57441271137b69b8a6e1c2dfe7e1e71`。

本地最新反馈已从此前 9 个失败收敛到 4 个失败：Agent 调试上下文缺少系统提示词、Integration Event 详情测试缺少 descriptions 组件注册、Organizations 文本断言受表格测试桩影响、Workflow 查询测试未设置运行记录 ID。

## 2. 本轮修复

### Agent 调试上下文

遵循 `FRONTEND_DEVELOPMENT_GUIDELINES.md` 的 Agent 规则，对话调试打开后按真实 `agent_id` 调用 `getPublishedVersion`，展示当前生效版本的系统提示词，并提供独立 Loading / Error 状态。页面不复制 Agent 状态机，调试请求仍只使用真实 `agent_id`。

### Integration Event 详情测试

生产页面已经使用正式中文字段 `幂等标识`。测试补齐 `ElDescriptions` / `ElDescriptionsItem` 组件注册，避免测试环境将业务详情组件当作未解析组件而丢失标签文本。

### Organizations 页面

组织页继续保留真实 `/organizations/{id}` 成员管理深链，并增加明确的用户提示“进入组织详情可管理成员”，使成员管理入口在高信息密度表格测试桩及窄屏信息层级中仍有可感知的业务说明。

### Workflow 查询测试

“查询运行记录”必须以真实 `execution_id` 为输入。测试在调用 `loadExecution` 前显式设置 `executionId = "e1"`，避免把空输入当成后端 Contract。产品代码不新增本地推断或平行状态机。

## 3. 兼容性与测试边界

- 不恢复旧英文 UI 文案。
- 不通过修改生产代码来迎合错误的测试输入。
- 不自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis。
- 不引入手工 token、用户名、密码、tenant ID、agent ID、workflow ID 或其他业务测试数据输入；测试数据继续由测试夹具提供。
- Agent 系统提示词仅展示后端正式 Published Version 返回值，不写入浏览器持久化存储。

## 4. 验证顺序

```powershell
npm test -- tests/views/Agents.test.ts tests/views/IntegrationEventConsole.test.ts tests/views/Organizations.test.ts tests/views/Workflows.test.ts
npm test
npm run build
npm run test:gate
npm run test:local:full
```

以上命令需在本地重新执行后才能记录为通过；本文件不预先声明尚未实际执行的结果。

## 5. 当前验收状态

本轮代码已针对用户提供的 4 个失败点完成修复设计与实现。最终验收仍以开发者本地实际执行结果为准。
