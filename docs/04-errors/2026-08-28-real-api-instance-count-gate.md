# Real API 测试错误：Worker / Scheduler 实例数量被错误限制

## 1. 现象

Real API Gate 在检测到多个 `run_worker.py` 进程时直接失败，并要求开发者停止旧 Worker，只保留一个当前 `main` Worker。该约束导致合法的多 Worker 本地运行环境无法进入真实 API 验收。

此前类似约束也容易把 Scheduler 的多实例运行误判为测试环境错误。

## 2. 根因

测试 Gate 将“服务可用性”和“服务实例数量”混为一体：

- Worker 的正确前置条件应为至少存在一个可用实例，而不是恰好一个实例；
- Scheduler 的正确前置条件同样不应限制实例数量；
- Durable claim、lease、checkpoint fencing、scheduled slot 幂等等规则本身就需要在多实例竞争环境中验证。

因此 `count != 1` 不是产品正确性的判定条件，也不能作为 Real API Gate 的通用阻断条件。

## 3. 修复

本次修复将 Real API Gate 调整为：

- Worker `count == 0`：阻断测试并提示启动 Worker；
- Worker `count >= 1`：允许继续测试，并输出实际实例数量与 PID；
- Tenant Safe Full Gate 同时要求至少存在一个 Scheduler；
- Scheduler `count >= 1`：允许继续测试，并输出实际实例数量与 PID；
- 不再要求开发者为了通过 Gate 手工停止重复 Worker / Scheduler。

## 4. 验证边界

该修复不会把“多实例”直接标记为产品通过。多实例只是合法测试环境；真实测试仍必须验证：

- Execution claim 唯一性；
- Worker lease / ownership fencing；
- checkpoint 写入边界；
- Resume 后的状态与 lineage；
- Scheduler slot claim 与幂等性；
- misfire / recovery 行为。

因此后续 Real API 验收应优先在 `Worker >= 1`、`Scheduler >= 1` 的环境执行，并增加明确的多 Worker / 多 Scheduler 并发场景。

## 5. 相关提交

- `test(real-api): allow multiple workers in durable resume gate`
- `test(real-api): allow multiple workers in tenant-safe gate`
- `test(real-api): require scheduler and allow multiple workers`
