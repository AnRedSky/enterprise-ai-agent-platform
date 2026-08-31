# UI-04 回归修复记录

## 变更范围

本次基于 frontend 分支最新本地测试反馈，修复 UI-04 状态契约、Dashboard 可测试性以及 UI-03 / Runtime Console 测试夹具问题。

### 根因与处理

| 失败 | 根因 | 处理 |
|---|---|---|
| AgentWorkbench loading | 列表加载状态初始值为 `false`，挂载瞬间存在 empty 状态窗口 | 将 `loadingAgents` 初始化为 `true`，保证首帧进入 shared loading state |
| AgentWorkbench success | 成功反馈使用 `StatePanel(success)`，导致成功表格之外仍存在 StatePanel | 成功反馈继续使用 `ElMessage`，成功表格保持唯一主内容 |
| AgentWorkbench 对话调试 | 测试中的 Element Plus table/column stub 没有透传 column default slot，导致操作按钮不可见 | 为测试提供最小可用 table/column slot stub |
| AuditLog loading | 审计列表 loading 初始值为 `false`，同样产生首帧 empty | 将 `loading` 初始化为 `true` |
| Dashboard metric-executions | 页面没有稳定的 metric test contract | 为 MetricCard 增加 `data-testid="metric-<key>"` |
| Tools UI-03 | 测试默认使用空工具数据，却要求 success-only 公共模式存在；Element Plus button slot 也未被测试 stub 渲染 | success 契约测试显式提供工具 fixture；button stub 透传 slot |
| Operations Console audit filter | 测试通过 `wrapper.text()` 查找 input placeholder，Element Plus input placeholder 不属于文本节点 | 改为按 `input[placeholder]` 语义查询 |

## 状态模型约束

列表页统一遵循：

`loading → permission/error/empty/success`

成功状态下不再使用 success `StatePanel` 作为内容占位；成功提示使用轻量 toast，避免状态面板与真实数据内容同时出现。

## 本地验证

在 `frontend` 目录执行：

```powershell
npm install
npm run test:unit -- --run tests/views/AgentUI04.test.ts tests/views/AuditLogUI04.test.ts tests/views/Dashboard.test.ts tests/views/Tools.test.ts tests/views/OperationsConsole.test.ts
npm run build
```

若执行完整回归：

```powershell
npm run test:unit -- --run
npm run build
```

测试数据必须由 Vitest fixture/mock 自动生成；不要依赖手工输入，也不要在测试脚本中自动启动后端服务。

## 结果记录

用户反馈的基线为 `40 passed / 8 failed`。本次提交针对 8 个失败项逐项修复代码或测试契约。由于 GitHub 远程开发工具无法复现用户 Windows 本地 Node/Vite 运行环境，本轮未伪造本地测试通过结果；最终通过状态必须在用户本地执行上述命令确认。
