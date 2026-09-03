# 2026-09-03 Delegation Real API Fixture 并发与异步契约问题

## 1. 现象

开发者在 Backend Regression Gate 的 tenant-safe Real API 阶段发现 Phase 2.8 Delegation 验收失败，并伴随 `RuntimeWarning`：

- B2/B3/B6 Fixture 在创建 Delegation 后断言 `model_profile_id` 时，API JSON 返回的是字符串 UUID，而测试辅助函数返回的是 `uuid.UUID` 对象，导致值相同但类型不同的断言失败；
- B4 cancel / timeout 与 B5 Audit / Trace 测试调用已经改为异步的 `_create_delegation()` 时遗漏 `await`，因此出现 `coroutine was never awaited` 警告并进一步触发 `TypeError: cannot unpack non-iterable coroutine object`；
- 真实多 Worker 环境中的 B6 Provider / Runtime 失败必须在上述 Fixture 错误消除后重新判断，不能把当前 Fixture 契约错误误判为生产 Runtime 缺陷。

## 2. 根因

本轮问题包含三个独立但连续的测试/环境契约问题：

### 2.1 HTTP JSON UUID 与 Python UUID 类型边界不一致

Real API 响应经过 JSON 序列化后，`model_profile_id` 的协议类型是字符串；`_prepare_target_model_profile()` 是数据库测试辅助函数，返回 ORM 使用的 `uuid.UUID`。

原断言直接比较：

`response["model_profile_id"] == profile_id`

两侧 UUID 值相同，但 Python 类型不同，因此失败。

正确边界是：测试在 HTTP 层按 API Contract 比较字符串 UUID；进入数据库查询时再显式转换为 `uuid.UUID`。

### 2.2 异步 Fixture 调用遗漏 await

`_create_delegation()` 为了在 Delegation 可见前完成 Provider/Profile 装配，已经定义为 `async def`。B4/B5 仍按旧同步 Fixture 调用，导致：

1. `_create_delegation()` 只返回 coroutine，没有实际创建 Fixture；
2. 直接解包 coroutine 产生 `TypeError`；
3. coroutine 没有被等待，pytest 在警告策略下报告 `RuntimeWarning`；
4. Real API Gate 因测试实现错误提前失败，无法继续验证真实 Delegation Runtime。

### 2.3 Real API Gate 使用了陈旧的 origin/main 远端跟踪引用

用户本地 Gate 输出曾报告：

`[PASS] HEAD == origin/main: bcb1a8fd2538c10b83eb6646e35484e0205bca46`

但 GitHub `main` 随后已经继续推进到 `1c46ded7d153567b053c8acae39a608a0a90f342`。原 Gate 只执行 `git rev-parse origin/main`，没有先刷新远端跟踪引用，因此“HEAD == origin/main”只能证明本地 checkout 与**旧的**远端引用一致，不能证明工作树基于最新 `main`。

更关键的是，用户本地 Real API 运行进程也可能仍来自旧代码。当前 `main` 的正式 `/auth/register` Contract 会把新用户创建到 `DEFAULT_TENANT_ID`，并在默认 Organization 中创建 active `member` membership；如果正在运行的 API 进程仍是旧版本，则 Bootstrap 注册后的新用户可能无法出现在 Organization members 中，从而产生：

`Registered fixture user is not present in the default Organization membership list`

因此这次现象不能通过修改生产认证逻辑或向 Fixture 强行写 membership 来掩盖。

## 3. 修复策略

### 3.1 收紧 HTTP Contract 断言

B2/B3/B6 共用 Fixture 将 `model_profile_id` 断言改为：

`assert response["model_profile_id"] == str(profile_id)`

不修改生产 API 的 JSON Contract，也不把数据库 UUID 强行改成字符串存储。

### 3.2 所有共享异步 Fixture 调用显式 await

B4 与 B5 的所有 `_create_delegation()` 调用统一改为：

`await _create_delegation(...)`

这样测试实际执行 Provider/Profile 装配、HTTP Delegation 创建和后续断言，并消除未等待 coroutine 警告。

### 3.3 Real API 源码基线 Gate 先刷新 origin/main

`backend/scripts/dev/verify_real_api_source_baseline.ps1` 现在在读取 `origin/main` 前执行：

`git fetch --quiet origin main`

然后再比较 `HEAD` 与最新 `origin/main`。这样本地 Gate 不再把陈旧远端跟踪引用误判成最新 main。

该修复只刷新 Git 远端引用，不启动、重启或停止任何 API / Worker / Scheduler / PostgreSQL / Redis 服务。

## 4. Tenant-safe Bootstrap 规则

`backend/scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py` 的入口显式清除 `API_TEST_USERNAME` / `API_TEST_PASSWORD`，随后由通用 Bootstrap 自动生成唯一 owner 用户。

这样保证：

1. owner 通过 `/auth/register` 创建并进入当前默认 Tenant；
2. owner 对应 Organization 与后续注册 member 使用同一 Tenant；
3. member username/password 仍由 Fixture 自动生成；
4. Organization、member、workflow、agent、provider、profile 等测试实体继续由脚本自动生成；
5. 不要求开发者填写测试用户名、密码、Tenant ID、Organization ID 或其他业务 ID；
6. 不修改生产 `/auth/register` 的 Tenant 语义；
7. Gate 仍禁止启动、停止或重启 API / Worker / Scheduler / PostgreSQL / Redis。

## 5. 与此前并发问题的关系

此前 B4/B2 已发现真实多 Worker 环境中的观察窗口问题：

- B4 必须使用 `claim_delegation(commit=False)`，把 Claim、Worker Execution、Frontier 与 `timeout_at` 放进同一事务；
- B2 不得在 Delegation 已进入 `completed` 后调用只接受 `running` 的 `AgentDelegationRuntimeBridge`；
- B6 必须继续保持 `completed` 为成功条件，不能通过接受 `failed` 来隐藏 Provider/Runtime 装配错误。

本轮 UUID 类型、异步调用、Tenant-safe owner 身份以及陈旧 `origin/main` 引用问题均属于 Fixture / 测试编排 / 环境基线层问题，必须先修复，再对 B6 的真实 Provider 运行结果进行判断。

## 6. 验证要求

按开发准则，Real API Gate 不负责创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis。依赖服务缺失时只报告 `[NOT EXECUTED]` 并给出标准启动命令；测试数据、租户、用户、业务实体与幂等信息必须由 Fixture 自动生成和清理。

更新本地工作树并确保运行中的 API 使用同一最新代码后，再执行：

```powershell
cd backend

git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD

uv run pytest -q -W error tests/api_real/test_agent_delegation_bridge_api.py tests/api_real/test_agent_delegation_b4_api.py tests/api_real/test_agent_delegation_b5_audit_trace_api.py tests/api_real/test_agent_delegation_multi_worker_api.py tests/api_real/test_agent_delegation_multi_worker_diagnostics.py

uv run pytest -q -W error

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

如果 B2/B3/B4/B5/B6 Fixture 契约错误全部消失后仍出现 `Mock provider HTTP 503`，再进入 Provider → ModelProfile → AgentVersion → Worker Runtime 的真实装配链路诊断；不得提前放宽业务成功断言。
