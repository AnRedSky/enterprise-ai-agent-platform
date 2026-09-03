# 2026-09-03 Delegation Real API 并发 Fixture 竞争问题

## 1. 现象

开发者在最新 Backend Regression Gate 的 tenant-safe Real API 阶段发现 3 个失败：

- B4 timeout：测试调用 `claim_delegation()` 时，真实后台 Worker 已经把 Delegation 从 `pending` 认领为 `running`；
- B2 bridge：测试等待 Delegation 进入终态后才调用 `AgentDelegationRuntimeBridge.load()`，此时正常 Worker 已经把 Delegation 收敛为 `completed`，而 Bridge 按设计只接受 `running`；
- B6 multi-worker：至少一个 Delegation 最终为 `failed`，错误为 `Mock provider HTTP 503`，该问题仍需要下一轮真实环境复现定位，当前不能通过放宽 `completed` 断言掩盖。

## 2. 根因

B4 与 B2 的主要问题不是生产状态机错误，而是 Real API Fixture 与真实多 Worker 环境之间存在非原子观察窗口：

1. Fixture 通过 HTTP 创建并提交 `pending` Delegation；
2. 已运行的 Worker 可以在测试 Session 再次 Claim 之前合法取得该 Delegation；
3. B4 原先在 `claim_delegation()` 返回后才设置 `timeout_at`，因此无法保证测试 Worker 获得可控的 Claim generation；
4. B2 原先在 Worker 执行结束后再调用 Runtime Bridge，而 Bridge 的契约明确要求 Delegation 必须处于 `running`，因此 `completed` 是正常的生命周期结果而不是 Bridge 缺陷。

## 3. 修复策略

### 3.1 Claim 暴露显式事务边界

`claim_delegation()` 增加 `commit=True` 参数：

- 默认保持原有直接调用语义；
- `commit=False` 时只执行 flush，不提交；
- 调用方可以把 Claim、Execution、Frontier、Audit、Trace 与后续治理事实放入同一事务。

B4 使用 `commit=False`，在同一事务内完成：

`pending → running + Worker Execution + Frontier + timeout_at → commit`

这样后台 Worker 在事务提交前无法观察到本次 Claim generation。

### 3.2 B2 Fixture 原子装配 Profile + Claim

B2 将 Mock Profile 装配与 Claim 放入同一事务，并使用 `claim_delegation(commit=False)`。如果 Fixture 仍处于 `pending`，测试 Worker 在提交前取得确定 ownership，然后执行对应 Frontier。

同时不再在 Delegation 已经进入终态后调用只允许 `running` 的 Runtime Bridge；Bridge 上下文验证必须发生在执行窗口内，终态验证单独检查最终持久化事实。

## 4. B6 处理原则

B6 的 `Mock provider HTTP 503` 尚未被认定为测试问题。测试使用 `provider_type="mock"`、`model_name="mock-model"`，按当前 `ModelGateway` Contract 应直接进入 `MockModelProvider`，不会产生 503。

因此下一轮必须继续检查：

- Target Agent Version 的 `model_profile_id`；
- Profile 的 `provider_id` 与 `provider_type`；
- Worker Runtime 实际装配的 profile/provider；
- 失败 Worker Execution 的 `error_code/error_message/output_data`；
- 多 Worker 同时运行时是否存在旧 generation / 错误 profile 读取。

禁止把 B6 期望值从 `completed` 放宽为 `failed`，否则会掩盖 Mock Provider 路由或 Runtime 装配错误。

## 5. 验证要求

下一轮本地验证必须在当前项目的真实 API / PostgreSQL / 多 Worker 环境中执行，Gate 不负责启动或停止任何服务。测试数据继续由 Fixture 自动生成并清理。
