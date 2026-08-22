# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已通过本地 Gate。
- 2.2-C Real Provider Quality Gate：已通过本地真实 Provider Gate，并已冻结 baseline。
- 2.2-D Retrieval Quality Regression：回归比较已通过，当前继续推进 Citation correctness 与 Retrieval Debug / Audit / Observability 追踪。

## 本轮实际验证

```text
Ollama embedding smoke: PASS
  provider=ollama
  model=nomic-embed-text:latest
  dimension=768
  vector_count=1

Backend regression: 301 passed, 30 deselected
Migration head: 0024_embedding_dimension_contract
Real HTTP API: 30 passed

2.2-C real-provider-pgvector:
  cases=5
  successful_cases=5
  error_cases=0
  error_rate=0
  fallback_count=0
  fallback_used=false
  recall@3=0.6
  precision@3=0.333333
  mrr=0.6
  quality_gate=passed

2.2-D baseline regression:
  identity_changed=false
  recall delta=0
  precision delta=0
  mrr delta=0
  provider_error_rate=0
  quality_gate=passed
```

真实 Provider 使用本地 Ollama `nomic-embed-text:latest`，实际维度为 768；评测真实写入 PostgreSQL/pgvector，未使用 fallback。首次 `--freeze-baseline` 已由开发者本地实际执行，随后再次执行 runner，baseline status=checked 且 regression Gate=passed。

当前真实 baseline 的语义质量为 Recall@3=0.6、Precision@3=0.333333、MRR=0.6。这组数据是当前 Provider / model / dataset / retrieval-mode 的回归基线，不应被表述为绝对质量达标，也不得通过修改指标、fallback、截断或补零人为提高结果。

已完成 Ollama 本地 503 / runner 启动 / 环境代理问题的修复，并记录工程错误。当前 Ollama 日志已确认 `/api/embed` 返回 200。

## 下一步

1. 继续 Phase 2.2-D：为 Evaluation Case 增加可验证的 Citation correctness 证据。
2. 将评测结果与现有 Retrieval Debug / Audit / Observability 建立可追踪关系；不得把评测 JSON 当作线上业务数据源。
3. 保持 Backend / Frontend / Browser Gate 独立。
4. 对 Provider / model / dimension / dataset / retrieval mode / top-k 的变化继续执行 baseline regression。
5. 当前 baseline 质量较低但稳定；在没有新的真实数据或明确质量目标前，不人为抬高绝对阈值，也不重写 baseline 来掩盖现状。
