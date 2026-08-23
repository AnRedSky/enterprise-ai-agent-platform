# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- 2.2-A Contract：已完成。
- 2.2-B Dataset / Runner：已完成，并有开发者实际执行验证。
- 2.2-C Real Provider Quality Gate：已通过真实 Provider baseline regression。
- 2.2-D Retrieval Quality Regression / Traceability：已完成并有 Real API evidence。
- 2.2-E Model Provider / Model Profile Governance Foundation：E-1、E-2、E-3、E-4 全部完成；E-4 三层 Gate 已由开发者本地实际执行通过。
- Phase 2.3 Model Provider Governance：**进行中 / 2.3-A Contract 已实现，等待开发者本地 targeted test 验证**。

## E-4 最终实际验证证据

开发者在当前修复后的 `main` 上实际执行：

```text
Backend Real API Gate:
  32 passed in 58.51s

Frontend Regression Gate:
  18 test files passed
  75 tests passed
  vue-tsc -b passed
  Vite production build passed

Model Provider/Profile Browser E2E:
  2 passed in 8.1s
```

三层 Gate 均通过，因此 **E-4 Passed / Phase 2.2 Closed**。

## E-4 已完成修复

- `448e2f8`：修复 Real API Model Provider Governance 测试 fixture 的 member boundary。
- `be5b9ca`：修复 Model Provider/Profile Browser E2E 的 Element Plus `el-select` selector 点击定位。
- `bfe6512`：修复 Model Provider/Profile AuditLog 的 organization-scoped 查询范围。
- `04c23de`：修复 Browser E2E Profile 名称字段的 strict locator 冲突。
- `92568e2`：清理 AuditLog error-path 单测预期 `console.error` 噪声，同时保留对错误日志行为的显式断言。

## Phase 2.2 最终结论

Phase 2.2 已满足 Retrieval Quality、Real Provider、Evaluation、Runtime Profile、Provider/Profile Governance、Frontend 与 Browser acceptance requirements，并完成 Acceptance / Phase / Status 同步。

Phase 2.2 正式关闭；不得继续向已关闭 Phase 2.2 塞入新的 Provider routing / fallback / cost / usage 功能。

## Phase 2.3 当前执行进度

### 2.3-A Provider Governance Contract — 已实现，待本地验证

已新增可执行 Backend Contract：`backend/app/services/model_provider_governance_contract.py`，并新增 `backend/tests/unit/test_model_provider_governance_contract.py`。

本任务冻结并以代码断言以下规则：

1. Provider routing strategy：默认 `explicit_profile`；没有显式 Profile 时不得隐式挑选 Provider；`organization_default` 必须按 enabled、model type、capability 与 provider allowlist 过滤并稳定排序。
2. Fallback eligibility：仅 connectivity、timeout、rate limit、provider 5xx；默认最大尝试次数 2；认证、参数、能力不匹配等错误不得自动 fallback。
3. Model whitelist / capability constraints：使用 Provider/Profile identity、model type、capabilities 与 provider allowlist，不硬编码具体模型名称。
4. Cost accounting：显式 usage unit + pricing source + pricing version；未获得真实 usage 时不得隐式估算冒充真实成本。
5. Usage accounting identity：organization/provider/profile/model_type/request/trace/outcome 可追踪，Secret 不进入 usage identity。

**本地验证状态：Pending。** 本轮没有把未执行的 targeted test 记录为 Passed。

下一任务：**2.3-B Backend Domain + API Contract**，将路由策略与治理策略接入真实 Provider/Profile 数据链路；涉及持久化时先 Migration，再进入 Backend tests / Real API。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result / baseline。
- 新业务代码不得新增具体模型名称硬编码；UI 测试中的模型字符串仅作为 fixture contract。
- 新增数据库表或字段必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance 必须独立 Product Contract，不得因 2.2 关闭而绕过 Contract 直接扩展。
