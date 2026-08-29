# Phase 2.8 B6 Multi-Worker Runtime Gate 失败记录

## 1. 发生时间

2026-08-29

## 2. 现象

B6 Multi-Worker Runtime Gate 在本地 Real HTTP + PostgreSQL 阶段出现两个失败：

1. 多 Worker 验收在两轮 `dispatch_once()` 后立即检查 Delegation 终态，部分 Delegation 仍为 `running`。
2. B2 Target Agent Runtime 验收出现 `503 Service Unavailable`，请求进入 `http://127.0.0.1:3477/v1/chat/completions`，与测试 Fixture 预期的 Mock Provider 不一致。

此前同一 Gate 还暴露过 `2/4` dispatch 计数问题；该问题已经由 Claim 返回 `worker_execution_id` 直接定位 Frontier 的实现修复，当前测试不再使用本地 dispatch 返回值作为总消费事实。

## 3. 根因分析

### 3.1 多 Worker 终态检查时序错误

`dispatch_once()` 的职责是完成一次 Worker 调度循环，不等价于所有异步 Runtime 已经完成。测试在 dispatch 返回后立即断言 Delegation=`completed`，形成了“调度完成”与“业务终态完成”的时序混淆。

正确验收边界应为：

```text
Claim Frontier
    ↓
execute_frontier
    ↓
WorkflowExecution terminalization
    ↓
Frontier terminalization
    ↓
Delegation completion/failure
    ↓
Real PostgreSQL assertion
```

修复后的测试直接使用两个独立 Worker 的 `claim_one_frontier()` + `execute_frontier()`，并在最终数据库断言前等待本次 Fixture 集合全部进入终态。

### 3.2 B2 503 Provider 路由异常

当前 Runtime Gateway 已规定：显式 `ModelProfile` 由治理服务解析后，按照 Profile 对应 Provider 类型选择技术 Provider；`provider_type=mock` 应进入 `MockModelProvider`，而不是 OpenAI-compatible HTTP Provider。

本次堆栈实际显示 Provider 请求进入 `127.0.0.1:3477`，因此该失败首先需要确认运行时实际解析出的 `ModelProfile/ModelProvider` 是否仍为 Fixture 创建的 Mock Profile。不能为了通过验收而把所有 5xx 强制降级到 Mock Provider，因为项目开发准则明确禁止用 Mock 成功结果替代真实 Provider 治理链路。

在未取得实际数据库行与运行进程配置证据前，不修改生产 Provider 路由代码。

## 4. 修复措施

- 多 Worker Real API 测试改为直接覆盖 `claim_one_frontier()` 与 `execute_frontier()` 正式 Runtime 边界。
- 增加 Delegation 终态等待窗口，防止异步 Runtime 调度完成与持久化终态之间产生测试竞态。
- 保留 Claim AuditLog、`worker_execution_id`、Frontier `attempt` 与终态联合断言，继续验证一次性消费事实。
- 不修改 Execution terminalization fencing。
- 不增加第二套 Queue / Retry / Recovery。
- B2 503 暂不通过 mock fallback 掩盖，待下一次本地 Gate 根据实际 Provider/Profile 数据继续定位。

## 5. 验证要求

必须重新执行 B6 Gate，并以本地实际结果更新 Phase / Acceptance / Project Status；不得预填通过。

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```
