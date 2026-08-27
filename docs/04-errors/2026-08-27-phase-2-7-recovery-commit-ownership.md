# Phase 2.7 Recovery Commit Ownership

- 日期：2026-08-27
- 阶段：Phase 2.7-A Durable Recovery Closure
- 类型：Transaction Boundary / Recovery
- 状态：已修复

## 问题

`resume_from_latest_checkpoint()` 在完成 Resume Candidate、幂等竞争处理以及治理事件写入后直接调用 `Session.commit()`，导致领域服务隐式取得整个 Recovery transaction 的提交权。

这与方法自身声明的“同一调用方事务”边界不一致，也使未来需要把 Resume 与其他 Durable Recovery 写入组合为单事务时缺少安全入口。

## 修复

`WorkflowExecutionService.resume_from_latest_checkpoint()` 增加显式 `commit` 参数：

- `commit=True`：保持现有独立调用兼容行为，由服务提交并刷新 Resume；
- `commit=False`：服务只完成 Domain Durable Write，不提交事务，由调用方拥有 commit 生命周期。

HTTP Resume endpoint 显式使用 `commit=False`，完成服务调用后由 API request transaction 执行唯一 `commit()`，随后 refresh 返回对象。

## 不变量

```text
Recovery caller
      |
      +-- Source Execution lock
      +-- Recovery Assessment
      +-- Resume INSERT / SAVEPOINT
      +-- Resume audit / trace
      |
      +-- exactly one caller-owned commit
```

Resume idempotency `IntegrityError` 仍只允许回滚 `begin_nested()` SAVEPOINT，不得调用整个 Session rollback。

## 验证

新增 `backend/tests/unit/test_workflow_resume_commit_ownership.py`，固定 Resume service 的显式 commit ownership Contract。

当前按开发策略暂停完整测试流程；未在本环境实际执行 pytest，因此不得将 Unit Test 记录为 PASS。
