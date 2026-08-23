# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**进行中 / E-3 Frontend Provider/Profile Management 已通过开发者本地 Frontend Gate，当前进入 E-4 Acceptance evidence 汇总。**
> 未执行的 Gate 不得标记 Passed。

## 1. 已验证 E-2 Evidence

开发者此前本地实际反馈：

```text
13 targeted tests passed
Migration head: 0027_alretrieval_evaluation_vector_space
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

## 3. E-3 Frontend Acceptance

### 3.1 已提交实现

- [x] Frontend Model Provider/Profile API types/client。
- [x] Organization-scoped Provider/Profile 管理页。
- [x] Provider CRUD UI。
- [x] Profile CRUD UI。
- [x] Chat / Embedding dimension boundary。
- [x] Credential reference 仅显示引用，不回显 Secret。
- [x] Frontend API/UI Vitest。
- [x] 测试环境 vue-router injection 修复。
- [x] Element Plus `DefaultRow` / `ModelProfile` production type boundary 修复。

### 3.2 开发者本轮实际执行证据

开发者在当前 main `0a4462a` 上实际反馈：

```text
Targeted Vitest:
  tests/api/modelProviders.test.ts + tests/views/ModelProviders.test.ts
  2 test files passed
  6 tests passed

Frontend Regression Gate:
  18 test files passed
  75 tests passed
  production build: passed
  vue-tsc -b: passed
  Vite build: passed
  built in 5.41s

Browser E2E:
  Phase 2.1-F organization browser contract
  3 tests passed
```

其中 Browser E2E 是既有 Organization governance contract，不等同于 Model Provider/Profile 专项 Browser E2E；本轮不把它冒充为 E-3 Provider/Profile Browser evidence。

### 3.3 E-3 结论

- [x] E-3 targeted Vitest 已由开发者实际执行并通过。
- [x] Frontend Regression Gate 已由开发者实际执行并通过。
- [x] production `vue-tsc` / Vite build 已通过。
- [x] 既有 Organization Browser E2E 保持通过。
- [ ] Model Provider/Profile 专项 Browser E2E：当前未执行；本阶段不作为 E-3 Passed 的必要条件。

因此 **E-3 可标记为 Passed（基于本轮开发者本地实际执行证据）**。

## 4. E-4 Acceptance 当前任务

E-4 不再修复 E-3 前端阻塞，改为汇总并核对以下已完成证据：

```text
E-2 Runtime / Evaluation Profile Resolution
    +
E-2 cross-dimension Real Provider evidence
    +
Provider/Profile CRUD + Organization scope + Audit
    +
E-3 Frontend targeted Vitest
    +
E-3 Frontend Regression Gate
    +
既有 Browser Organization governance evidence
    ↓
E-4 Acceptance decision
```

E-4 必须保持 Backend / Frontend / Browser Gate 独立，不能用 Frontend 结果替代 Backend Real API evidence，也不能用既有 Organization Browser E2E 冒充 Provider/Profile 专项 E2E。

## 5. E-4 下一步执行顺序

1. 核对当前 main 上 E-2 / E-3 代码、Migration、Backend Real API、Runtime / Evaluation / Audit / Trace evidence 与文档是否一致。
2. 如发现 Acceptance 文档使用了过期 commit、旧测试数量或未重新执行结果，必须改为当前可追溯证据。
3. 完成 E-4 Acceptance 结论后，再决定 Phase 2.2 是否关闭；不得因为 E-3 Frontend Gate 通过而提前关闭 Phase 2.2。
4. Phase 2.3 Provider routing / Fallback / cost / usage governance 不得提前实现。

Frontend Gate 不调用 Backend regression、Alembic 或 Real API Gate；Browser E2E 不重复 Backend/Frontend regression。
