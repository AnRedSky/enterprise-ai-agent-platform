# Resume Checkpoint Lineage 边界错误记录

## 发现

Resume Contract 已经把 `resume_checkpoint_sequence` 写入新 Execution，但 Bootstrap 直接接收 Source / Resume Execution 后没有再次验证该字段是否仍然指向 Source 的实际可恢复 Checkpoint。

这意味着绕过标准 Contract、直接调用 Bootstrap 时可能形成：

```text
Source Checkpoint #N
        ↓
Resume.resume_checkpoint_sequence = #M
        ↓
completed Node lineage / Frontier
```

其中 `N != M`，导致 Resume 的幂等 identity 与实际恢复快照脱节。

## 根因

`resume_checkpoint_sequence` 的语义是 **Source Checkpoint lineage**，不是 Resume Execution 未来自身 Checkpoint 的序号。此前该语义主要由 Resume Contract 保证，Bootstrap 缺少最后一道领域边界校验。

## 修复

Bootstrap 在复制 Node Durable Facts 前：

1. 使用当前 Source Execution 的 tenant scope 读取 `latest_recovery_fact()`；
2. 要求 Source Checkpoint 存在；
3. 要求 `resume_execution.resume_checkpoint_sequence == source_checkpoint.sequence`；
4. 任一条件失败立即拒绝 Bootstrap；
5. Resume 自身未来产生的 Checkpoint sequence 继续独立属于 Resume Execution。

## 边界

```text
Source Execution
  └── Checkpoint #N
          │
          │ lineage
          ▼
Resume Execution
  └── resume_checkpoint_sequence = N

Resume Execution 后续新 Checkpoint
  └── sequence 从自身 Execution 的 Durable Checkpoint 序列继续分配
```

这样 Source lineage 与 Resume 自身 Checkpoint sequence 不再混用。

## 测试

增加 Unit Test 覆盖：

- Source / Resume sequence 一致；
- Resume sequence 缺失；
- Resume sequence 漂移。

当前阶段按开发策略暂停完整测试流程；未在本环境实际执行 pytest，因此不得将上述测试记录为已通过。
