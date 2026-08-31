# Frontend Full Vitest Regression Remediation — 2026-08-30

## 1. 本次基线

`main` 与 `frontend` 当前已同步，最新共同提交为 `4e9c04c9f21f95d202ea5ee26bd1e807540a562b`。

本地最新反馈为 34 个测试文件中 2 个失败、153 个测试中 2 个失败，集中在 Runtime Operations 页面：诊断请求全部失败时全局态势仍应可见并给出安全错误提示；Operations Console 全局 Tab 的异步数据尚未完成渲染时测试过早断言业务内容。

## 2. 本轮修复

### Global Runtime Operations

诊断区域的可见条件由“存在诊断数据”扩展为“存在全局态势或诊断错误”。因此 Worker / Scheduler 诊断请求同时失败时，页面仍保留诊断区域，并展示用户可理解的“诊断数据暂时不可用；全局运行态势仍可继续查看。”提示；不会展示后端原始异常文本。

### Operations Console

全局运行态势测试改为等待正式 `runtimeOperationsApi.global` 调用完成并等待“执行总量”进入 DOM，再断言后端返回的执行数量、运行态和 Workflow 数据。该调整只修正异步组件测试的同步点，不降低业务断言，也不改变生产代码或 Backend Contract。

## 3. 兼容性与测试边界

- 保持现有中文 UI 文案和 Runtime Durable Facts 语义。
- 不复制 Worker / Scheduler 生命周期或心跳判断。
- 不展示 `Error.message`、HTTP 错误正文或异常堆栈。
- 不自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis。
- 测试数据继续由测试夹具自动提供，不要求手工填写业务信息。

## 4. 验证顺序

```powershell
npm test -- tests/views/GlobalRuntimeOperations.test.ts tests/views/OperationsConsole.test.ts
npm test
npm run build
npm run test:gate
npm run test:local:full
```

以上命令必须在本地重新执行后才能记录为通过；GitHub 端代码变更本身不等同于本地测试通过。

## 5. 当前验收状态

本轮已完成代码与回归测试修复设计。由于当前执行环境无法直接运行用户 Windows 工作树中的 npm 命令，最终验收状态保持为“待本地验证”，不得预先声明测试通过。
