# UI-04 Workflow 状态迁移记录

## 范围

本轮只处理 `frontend/src/views/workflows/index.vue`，不修改 Workflow API Contract、领域状态机或后端接口。

## 状态映射

| 页面场景 | UI-04 状态 | 行为 |
|---|---|---|
| 首次加载工作流且暂无数据 | Loading | StatePanel，保留刷新入口 |
| 查询成功但没有工作流 | Empty | 提供创建/刷新方向 |
| 工作流查询失败 | Error | 提供重试 |
| HTTP 403 | Permission | 独立于 Error，不显示“重试”作为唯一解释 |
| 创建、更新、版本、发布、运行等操作完成 | Success | StatePanel + 原有消息反馈，并重新同步数据 |
| 运行记录、审计、运行链路 | Loading / Empty / Error / Permission | 各自维护局部状态，不污染页面级状态 |

## 实现决策

1. `StatePanel` 只负责状态表达和恢复入口，不承担 API、权限判断或 Workflow 领域状态机。
2. HTTP 403 通过错误响应状态转换为 Permission；其他失败保持 Error。
3. 运行记录、审计、运行详情和 Trace 分别维护自己的状态，避免一个请求失败覆盖整个页面。
4. 原有 Element Plus `loading` 按钮状态继续保留，用于动作进行中的即时反馈；页面级数据状态统一由 `StatePanel` 表达。
5. Success 不替代服务端刷新；成功写操作仍然调用原有 reload/select 流程。
6. 原有 Workflow 状态枚举、版本发布、执行、取消、重试、恢复逻辑不改变。

## targeted test

新增 `frontend/tests/views/WorkflowUI04.test.ts`，验证：

- StatePanel 五类状态全部接入；
- Permission 与 Error 分离；
- Success 与重试反馈保留；
- 不修改 API Contract。

## 本地验证

```powershell
cd frontend
npm test -- tests/views/WorkflowUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

当前远端开发环境没有执行本地 Node/Vitest/build，因此本记录不声明测试通过。

## 后续

UI-04 下一轮继续只选择一个核心页面，优先 Runtime；完成后再评估是否需要把局部状态进一步抽象为表格/操作级公共模式。
