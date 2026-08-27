# 2026-08-27 Replay Decision Convergence 边界

## 问题

`WorkflowRecoveryTraceLinkService.record_dag_decision()` 原先只按当前 `decision_id` 查询幂等记录。若相同 `trace_id + tenant + workflow version + completed Node facts` 在 Replay 时产生了新的 fingerprint，该调用会因为旧 fingerprint 不匹配而查不到记录，随后继续写入第二个 Decision Trace。

这会破坏 Phase 2.7 的核心不变量：**相同 durable completed facts 必须收敛到同一个 Decision**。仅依赖数据库的“相同 decision_id 幂等”不足以阻止历史 Decision payload 漂移。

## 根因

Replay Convergence Guard 已经存在于 `assert_dag_decision_replay_consistent()`，但 `record_dag_decision()` 没有在创建 Decision 前调用它，因此 Guard 没有成为写入边界。

```text
Planner Decision
      ↓
record_dag_decision()
      ↓
原先：按 decision_id 查询
      ↓
旧 fingerprint 不同 → 查不到 → 新增第二条 Decision
```

## 修复

`record_dag_decision()` 现在在任何数据库写入前先调用 `assert_dag_decision_replay_consistent()`：

- 同一 tenant + workflow version + trace + completed Node facts 的历史 Decision 必须与当前 fingerprint 一致；
- frontier 不一致时拒绝 Replay；
- selected predecessor 不一致时拒绝 Replay；
- 检查通过后才执行当前 `decision_id` 的幂等查询；
- 冲突发生在 flush/commit 前，因此不会产生第二条 Decision Trace。

没有新增第二套 Decision 计算逻辑，仍由唯一 `WorkflowDagResumePlanner` 产生 fingerprint。

## 测试

新增 Unit Test：

- 验证 Replay 收敛检查先于 Decision 写入；
- 使用相同 durable completed facts + 不同 fingerprint 验证直接拒绝；
- 验证冲突时不会 `add / flush / commit`。

当前环境无法本地执行 pytest，因此本提交不记录 Unit Test PASS；仅记录测试实现完成，等待开发者本地实际执行。
