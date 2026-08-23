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

- `448e2f8`：修复 Real API Model Provider Governance 测试 fixture 的 member boundary，member token 现在明确对应 `member` membership，再验证 Provider/Profile 写操作 403。
- `be5b9ca`：修复 Model Provider/Profile Browser E2E 的 Element Plus `el-select` selector 点击定位。
- `bfe6512`：修复 Model Provider/Profile AuditLog 的 organization-scoped 查询范围。
- `04c23de`：修复 Browser E2E Profile 名称字段的 strict locator 冲突。
- `92568e2`：清理 AuditLog error-path 单测预期 `console.error` 噪声，同时保留对错误日志行为的显式断言。

## Phase 2.2 最终结论

Phase 2.2 已满足 Retrieval Quality、Real Provider、Evaluation、Runtime Profile、Provider/Profile Governance、Frontend 与 Browser acceptance requirements，并完成 Acceptance / Phase / Status 同步。

Phase 2.2 正式关闭；不得继续向已关闭 Phase 2.2 塞入新的 Provider routing / fallback / cost / usage 功能。

## 下一执行阶段：Phase 2.3 Model Provider Governance

根据 Product Roadmap，下一正式阶段是 Phase 2.3。进入条件为明确成本口径、路由策略与 Provider Contract。下一任务不是直接修改 2.2 foundation，而是建立独立的 2.3 Provider Governance Contract，并随后按产品开发矩阵执行 Backend Contract → Migration/Tests → Real API → Frontend/Browser（按实际范围裁剪）→ Acceptance。

Phase 2.3 首批必须冻结：

1. Provider routing strategy。
2. Fallback eligibility / failure semantics。
3. Model whitelist / capability constraints。
4. Cost accounting unit and pricing source。
5. Usage accounting dimensions and audit identity。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result / baseline。
- 新业务代码不得新增具体模型名称硬编码；UI 测试中的模型字符串仅作为 fixture contract。
- 新增数据库表或字段必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance 必须独立 Product Contract，不得因 2.2 关闭而绕过 Contract 直接扩展。
