# Durable Recovery Resume Trace 原子事务记录

日期：2026-08-27

## 问题

自动恢复原先由 Resume Contract 自行提交 Resume Execution / Node lineage / Frontier，随后 Recovery Service 再写入 `recovery.trace_linked`。这会把同一次 Recovery 拆成两个 commit：Resume 已持久化但 trace lineage 写入失败时，数据库会留下不完整的 Recovery 审计事实。

## 修复

- `WorkflowExecutionResumeContractService.resume_with_outcome()` 增加 `commit` 参数；默认保持直接调用兼容，自动恢复传入 `commit=False`。
- `WorkflowRecoveryTraceLinkService.link()` 增加 `commit` 参数；默认保持直接调用兼容，自动恢复传入 `commit=False`。
- `WorkflowExecutionAutomaticRecoveryService.recover()` 现在统一执行：Resume 创建 → completed Node lineage / 首个 Frontier Bootstrap → Recovery trace link → 外层 `COMMIT`。
- 任一步失败时由调用方事务统一回滚，避免产生孤儿 Resume Execution 或缺失 Recovery trace 的半完成恢复记录。

## 事务边界

```text
Source Execution lock
        ↓
Resume Contract(commit=False)
        ↓
Resume Node lineage + Frontier Bootstrap
        ↓
Recovery Trace Link(commit=False)
        ↓
单一外层 COMMIT
```

## 测试边界

已补充 Unit Test 验证 `Resume Contract` 可以将 commit 延迟给外层 Recovery transaction。按照当前开发策略，本轮未执行完整 pytest，因此不声明实际 PASS。