# 2026-08-28 Phase 2.7 Durable Frontier / DAG 回归 Contract 漂移

## 1. 问题

本地执行 Phase 2.7 targeted regression 时发现两组失败：

1. DAG 首次执行的多 root fixture 触发 `DAG Workflow 第一版 Resume 必须只有一个 root`。
2. Durable Frontier duplicate completion 测试 fixture 仍按旧查询链路模拟 `Checkpoint.scalar_one_or_none()`，而当前生产实现已经读取完整 completion Checkpoint 集合，并在 Replay convergence 前锁定关联 Execution 校验 lifecycle。

## 2. 根因

### 2.1 DAG Contract 与已交付 Multi-frontier Runtime 能力不一致

当前 Runtime/Planner 已把多个 root 视为首次执行的独立 frontier；Contract 却仍保留早期单 root 限制。该限制已经成为过时的生产 Contract，而不是应通过修改测试规避的测试问题。

### 2.2 Duplicate completion 测试 double 落后于生产锁边界

`complete_frontier_with_checkpoint()` 的 Replay 路径现在依次验证：

- source Frontier 是否已完成；
- completion Checkpoint 是否唯一且 payload 一致；
- 关联 Execution 是否存在并与 Checkpoint lifecycle 一致；
- 非 terminal Replay 是否存在完全一致的 Next Frontier identity。

旧测试只提供 Frontier + 单个 Checkpoint 查询结果，没有提供 Execution lookup；因此真实业务断言尚未执行就被 `MagicMock.status` 触发的 lifecycle guard 拦截。

## 3. 修复

- 移除 DAG Contract 的单 root 限制，保留至少一个 root、孤立节点和环路校验。
- 将 DAG Contract 单元测试改为明确验证 multi-root 合法性。
- 将 duplicate completion fixtures 对齐当前 `scalars().all()` completion fact 查询语义。
- 为 Replay convergence fixture 补齐 `execution_status`、Execution lifecycle、Next Frontier fingerprint 和 Node 集合。
- 将 targeted regression 入口扩展到 DAG / Frontier duplicate completion 全部相关测试。

## 4. 不变量

- DAG 可以存在多个 root；每个 root 在首次执行时可以形成独立 frontier。
- Completion fact 必须唯一；多个同 source completion fact 必须 fail-closed。
- Replay payload、Execution lifecycle、Next Frontier fingerprint 和 Node 集合必须与原 Durable fact 一致。
- Replay 不得重新执行 transition、commit 或生成第二条 Frontier。

## 5. 验证状态

本记录对应的修复提交后，必须由开发者在本地重新执行 targeted regression。未实际执行前不得记录 PASS。

推荐入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\workflow\01_resume_runtime_regression.ps1
```
