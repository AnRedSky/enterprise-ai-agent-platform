# Phase 1.8 Final Acceptance — Event / Webhook Trigger Expansion

> 状态：**正式关闭**
> 验收基线：`main`，2026-08-21

## 1. 验收范围

```text
Browser / External Event
 ↓
Vue Trigger Governance
 ↓
Backend HTTP API
 ↓
Webhook Authentication / Validation
 ↓
Durable Idempotency Claim
 ↓
Workflow Execution
 ↓
Execution Observation
```

## 2. 任务关闭矩阵

| 任务 | 状态 |
|---|---|
| 1.8-A | 已完成 |
| 1.8-B | 已完成 |
| 1.8-C | 已完成 |
| 1.8-D | 已完成 |
| 1.8-E | 已完成 |
| 1.8-F | 已完成并正式关闭 |

## 3. Backend Gate

开发者实际执行：

```text
uv run pytest -q
→ 257 passed, 20 deselected in 4.95s

scripts/test/api-real/01_run_real_api_tests.ps1
→ 20 passed in 37.94s
→ [PASS] Real API gate completed.
```

Phase 1.8-B 已实际执行 `uv run alembic upgrade head` 并通过；本阶段无新增 Migration。

## 4. Frontend Gate

```text
npm test
→ 13 test files passed
→ 52 tests passed

npm run build
→ succeeded
→ 1709 modules transformed

Frontend Regression Gate
→ [PASS]
```

## 5. Browser E2E

```text
3 tests listed
3 passed
```

覆盖 Webhook governance、runtime convergence、duplicate / authentication / lifecycle security。

## 6. Contract

- Webhook Trigger CRUD / enable / disable / delete。
- Secret 只写入，不泄露 `secret` / `secret_hash`。
- 非法 secret → `401`。
- 缺失事件身份 → `422`。
- disabled Trigger → `409`。
- 同一 Trigger + Event Identity 只产生一个 durable Execution。
- 超过 100 字符时使用 SHA-256 bounded idempotency key。
- 依赖数据库 `(tenant_id, idempotency_key)` 唯一约束。

## 7. Database

不新增数据库表或字段；不创建 `webhook_events`，不修改 `0022_workflow_trigger`。

## 8. 最终结论

**Phase 1.8 Event / Webhook Trigger Expansion 正式关闭。**

以上实际结果来自原 `PHASE_1_8_ACCEPTANCE.md` 与 `PROJECT_STATUS.md`，迁移不改变事实。