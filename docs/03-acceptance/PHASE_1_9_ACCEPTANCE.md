# Phase 1.9 Acceptance — Runtime Reliability / Production Hardening

> 状态：进行中
> 基线：最新 `main`

## 1. Acceptance 原则

本文件只记录开发者本地实际执行的验收结果，不预填 PASS，不使用 GitHub Actions 替代本地验收。

## 2. 1.9-A Acceptance

### Circuit Breaker HALF_OPEN Concurrent Recovery

| Gate | 实际结果 | 状态 |
|---|---:|---|
| Circuit Breaker targeted tests | 16 passed / 0.68s | PASS |
| Alembic upgrade head | PostgreSQL upgrade completed | PASS |
| Migration head | `0022_workflow_trigger` | PASS |
| Backend Regression | 262 passed, 20 deselected / 3.64s | PASS |
| Mandatory Real API | 20 passed / 32.99s | PASS |
| Standalone Real API | 20 passed / 33.26s | PASS |

结论：**1.9-A 已通过本地实际验证。**

## 3. 1.9-B Acceptance

### 当前实现

已完成 Runtime Failure / Retry / Circuit Boundary 的 stale Probe completion 修复：

- HALF_OPEN Probe reservation 继续受 PostgreSQL 行锁保护。
- Probe completion 绑定当前 Recovery Window。
- 使用现有 `half_opened_at` 作为 Recovery Window generation boundary。
- stale Probe success 不得关闭新的 Recovery Window。
- stale Probe failure 不得重新 OPEN 新的 Recovery Window。
- 未经过 `before_call()` 的直接 service-level success/failure 调用保持兼容。

对应代码提交：

```text
8085e5c7c6009a97a7d3a1d73094f7812c9f9258
fix: isolate stale circuit probe completions
```

对应专项测试提交：

```text
f7ef0c55810171cb70e5873a99cba82a01a64047
 test: cover stale half-open probe completion
```

### 本地实际验证

开发者在最新 `main` 实际执行：

| Gate | 实际结果 | 状态 |
|---|---:|---|
| Focused 1.9-B runtime tests | 35 passed / 0.97s | PASS |
| Backend Regression | 264 passed, 20 deselected / 4.79s | PASS |
| Alembic upgrade/head | `0022_workflow_trigger` | PASS |
| Mandatory Real API | 20 passed / 40.74s | PASS |
| Standalone Real API | 20 passed / 31.38s | PASS |

结论：**1.9-B 当前 focused scope 已通过本地 Backend / PostgreSQL / Real API 验证。**

### 1.9-B 当前边界

本次 Acceptance 已覆盖 stale Probe completion、Circuit Breaker 与 Retry/Timeout/Deadline 现有边界测试。当前没有发现需要继续修改代码的 1.9-B blocking issue。

后续可靠性专项进入 1.9-C。若 Real API 专项场景发现新的跨 worker、retry、idempotency 或 tenant isolation 问题，应新增错误记录并回到相应修复任务。

## 4. 下一验收顺序

1. 1.9-C Real API Reliability Scenarios。
2. 1.9-D Frontend / Browser Reliability Convergence。
3. 1.9-E Final Acceptance。

## 5. Phase 1.9 关闭条件

必须同时满足：

- 1.9-A Acceptance PASS；
- 1.9-B Runtime Failure / Retry / Circuit Boundary PASS；
- 1.9-C Real API Reliability PASS；
- 1.9-D Frontend / Browser Reliability PASS；
- Backend / Frontend / Browser 独立 Gate 均来自本地实际执行；
- Migration head 正确；
- PROJECT_STATUS 与 Phase 文档同步；
- 无未记录的阻塞错误。
