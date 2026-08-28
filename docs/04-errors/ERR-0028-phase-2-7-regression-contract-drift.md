# ERR-0028 — Phase 2.7 本地回归中的测试 Contract / Double 漂移

## 基本信息

- Canonical ID：ERR-0028
- 发现日期：2026-08-28
- 领域：Workflow / Durable Frontier / Durable Resume
- 来源：开发者本地 Phase 2.7 full regression
- 影响：74 failed / 143 passed / 3 warnings

## 问题现象

Phase 2.7 full regression 在 `45937aa` 后实际执行时，大量失败集中出现在 Durable Resume、Frontier progression、Claim、Checkpoint、Runtime 与 Recovery 测试。

主要失败模式包括：

1. 测试 double 未补齐生产 Contract 新增字段，例如 `tenant_id`、`node_id`、`worker_attempt`。
2. Async SQLAlchemy Session 的 `execute()`、同步 `add()` 等调用边界被错误建模，导致 coroutine 未 await、`coroutine` 属性访问等错误。
3. Frontier Claim 的生产实现已经切换到 `candidate → identity → Execution lock → Frontier lock → overlap check` 的锁序，旧测试仍按旧调用次数和返回形态构造 fixture。
4. Frontier identity 已按并行 Node 集合做 canonicalization，旧测试仍假设 Node 顺序属于 identity。
5. Condition short-circuit 测试的首个 `and` 子条件实际命中，导致测试误触发第二个 contains 分支，问题来自测试数据而非 Evaluator 的短路实现。
6. Resume idempotency race 测试在预检查阶段已经返回 existing，未真正进入 savepoint；测试没有模拟“预检查不存在、插入时发生唯一键竞争、竞争后读取 existing”的真实并发路径。

## 根因

本轮生产 Contract 连续收口后，部分 Unit Test fixture、Mock 和 source-contract assertion 没有同步演进。测试因此验证了已经废弃的调用顺序或不完整的对象形状，而不是当前 Durable contract。

这些问题不应通过放宽生产代码的 tenant boundary、ownership fencing、锁序或 checkpoint lifecycle guard 解决。

## 修复策略

本轮先修复已经明确可以判定为测试 Contract 漂移的问题：

- 为 DAG Resume fixture 补齐 `tenant_id`。
- 为 Resume checkpoint fake 补齐 `node_id`。
- 将 Resume idempotency race fixture 改为真正进入 `begin_nested()` 的竞争路径。
- 将 Frontier progression / lifecycle 测试的 DB double 调整为 `MagicMock + AsyncMock(execute/commit)`，保持 `db.add()` 为同步调用，消除 coroutine warning。
- 将 Frontier Claim fixture 更新到 Execution-first lock order 与 `one_or_none()` tuple identity contract。
- 将 Frontier identity 测试更新为 Node 集合 canonicalization 语义。
- 修正 Condition `and` short-circuit 测试输入，使首条件实际返回 False。

## 已提交修复

当前 main 已连续提交以下测试修复：

- `effb0db` — align resume runtime fixtures with tenant boundary
- `eb8ff9f` — align DAG runtime fixture with tenant-scoped resume contract
- `05c269f` — repair resume idempotency race transaction fixture
- `e21fd53` — complete resume checkpoint fixture contract
- `73badd0` — align frontier progression doubles with async DB contract
- `e808200` — fix frontier lifecycle async test doubles and warning sources
- `1251047` — align frontier claim fixture with execution-first lock order
- `5a3da98` — correct condition short-circuit fixture
- `799439f` — align frontier identity test with canonical node set

## 防止复发

1. Durable Contract 修改必须同步检查所有相关 Unit Test fixture。
2. AsyncSession mock 必须明确区分异步 `execute/flush/commit` 与同步 `add`。
3. 锁序、tenant boundary、worker epoch、checkpoint lineage 等 Contract 测试必须以当前生产调用顺序为准。
4. source-string assertion 只能验证稳定的设计约束，不应依赖已经不存在的具体措辞。
5. 回归脚本必须在每次 Contract 收口后重新执行；未实际执行不得标记 PASS。

## 当前验证状态

**代码修复已提交，但截至本记录生成时尚未由开发者在最新 main 上重新执行 full regression，因此不得标记为 PASS。**
