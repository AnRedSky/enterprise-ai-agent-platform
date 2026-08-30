# 审计日志体验加固

## 目标

本轮以现有 `GET /runtime/audit-logs` Contract 为唯一数据来源，完成 Audit 页面在 P1 可观测工作台中的渐进增强：筛选体验、错误恢复、Execution 深链和窄屏可用性。

## Contract 对齐

前端继续调用 `runtimeApi.auditLogs({ page, page_size, status? })`，不新增平行 API。AuditLog 保留后端返回的 `execution_id`、`agent_id`、`tool_id` 等真实技术标识；不在前端计算业务状态。

后端最新 RuntimeOperations Audit 查询已明确 tenant-scoped、limit 1~1000，并按 `created_at DESC, id DESC` 稳定排序。前端分页尺寸保持 10/20/50/100，避免依赖前端扩大后端查询边界。

## UI / 交互决策

1. 状态筛选改为有限枚举选择器，避免用户输入无效状态。
2. Empty 状态提供“查看全部记录”恢复动作。
3. Error 状态提供“重新加载”，只展示用户可理解的恢复提示，不暴露后端异常正文。
4. Audit 中存在真实 `execution_id` 时提供 Runtime 深链：`/runtime?execution_id=<id>&source=audit`。
5. Execution ID 在展示层做紧凑化，但路由始终携带完整真实 ID。
6. 表格保留横向滚动，窄屏下筛选和分页纵向排列，避免压缩技术字段造成误读。

## 性能与兼容性

- 页面仍仅在挂载时加载一次 Audit 列表；刷新/筛选/分页复用同一 API 方法。
- 不新增全局状态，也不预加载 Runtime Execution 详情；深链后由 Runtime 按现有上下文规则按需加载。
- 继续使用 Element Plus 标准组件和 `v-loading`，兼容当前应用入口注册方案。

## 自动化验证

目标测试：

```powershell
npm test -- tests/views/AuditLog.test.ts
npm test
npm run build
npm run test:gate
npm run test:e2e
```

本次代码提交不虚构本地执行结果。若本地依赖未安装或 Windows 文件锁导致 `npm ci` 失败，应先恢复项目依赖，再执行上述正式脚本。

## 本地全面测试脚本

建议使用 `scripts/test/run-local-full-regression.ps1`。脚本只负责依赖预检、前端测试、构建、Gate 和 E2E；不会自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis，也不会要求手工填写测试数据。E2E 所需服务必须由本地已有运行环境提供；缺失时脚本明确输出 `NOT EXECUTED` 和标准启动提示后停止。
