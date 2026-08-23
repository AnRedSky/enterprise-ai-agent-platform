# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / E-2 已完成当前定义范围，E-3 Frontend Provider/Profile Management 实现中。**
> 未执行的 Gate 不得标记 Passed。

## 1. 已验证 E-2 Evidence

开发者本地实际反馈：

```text
13 targeted tests passed
Migration head: 0027_retrieval_evaluation_vector_space
Backend regression: 323 passed, 31 deselected
Real HTTP API: 31 passed
Standalone Real API Gate: 31 passed
Governed smoke: status=passed
Profile A: nomic-embed-text:latest / 768
Profile B: qwen3-embedding:0.6b / 1024
retrieval_mode=real-provider-pgvector
retrieval_execution_path=runtime-service
fallback_count=0 / fallback_used=false
Profile B quality_gate=failed because model/dimension/model_profile_id identity changed; this is expected regression evidence
```

`Profile B quality_gate=failed` 不能单独解释为测试失败：Smoke 顶层 `status=passed`，其目的就是验证 governed identity 改变时不能复用 Profile A baseline。

## 2. E-2 Acceptance 结论

- [x] Cross-dimension Evaluation Vector Space 可实际使用 768 / 1024 Profile。
- [x] Production `knowledge_chunks` 未被 evaluation dimension 改写。
- [x] Profile / Provider / model / dimension identity 进入 evaluation report / baseline regression。
- [x] Backend regression / migration / Real API Gate 均有本地实际证据。
- [x] Governed smoke 实际通过，且未下载模型。
- [x] fallback 未被用于伪造 vector quality success。
- [x] Secret 不进入 report / trace / audit / Git。

因此 2.2-E-2 可标记为 **Passed（基于开发者本地实际反馈）**。

## 3. E-3 Frontend Acceptance 当前状态

### 已提交实现

- [x] Frontend Model Provider/Profile API types/client。
- [x] Organization-scoped Provider/Profile 管理页。
- [x] Provider CRUD UI。
- [x] Profile CRUD UI。
- [x] Chat / Embedding dimension boundary。
- [x] Credential reference 仅显示引用，不回显 Secret。
- [x] Frontend API/UI Vitest 实现。

### 待开发者本地执行

- [ ] E-3 targeted Vitest。
- [ ] Frontend Regression Gate：test → production build。
- [ ] Browser E2E（若本阶段纳入 UI 验收）。

以上未执行项不能记录 Passed。

## 4. 下一步验收顺序

```text
E-3 targeted Vitest
    ↓
Frontend Regression Gate
    ↓
Browser E2E（独立，可选）
    ↓
E-4 Acceptance evidence 汇总
```

Frontend Gate 不调用 Backend regression、Alembic 或 Real API Gate；Browser E2E 不重复 Backend/Frontend regression。
