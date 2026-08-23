# 产品需求与功能开发对比矩阵

> 基线：当前 `main`
> 目的：将“产品能力目标、当前实现、验收证据、明确缺口、下一步决策”放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有项目实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。

## 1. 当前核心能力

| 产品域 | 当前实现 | 验收状态 | 下一动作 |
|---|---|---|---|
| Runtime | Runtime + Session + Context + Model/Tool/Knowledge/Memory | 已验收历史范围 | 2.3-C 接入治理 routing |
| Model Gateway | Mock/OpenAI-compatible、普通/流式 Contract | 已覆盖当前范围 | 2.3-C 接入治理候选，禁止 Mock 伪造真实 Provider 成功 |
| Model Provider / Profile | Provider/Profile 数据模型、CRUD、Organization scope、Audit | **2.2-E 已验收** | 2.3-C Runtime Routing Integration |
| Provider Governance | executable routing/fallback/cost/usage Contract + `POST /model-providers/routing/resolve` | **实现完成，待本地验证** | 2.3-C |
| Observability | Execution/Event/Trace/Audit + UI | 已验收当前范围 | 2.3-C 接入 provider/profile/usage identity |
| Governance | Tenant/RBAC/Audit/Trace/Reliability | 已验收当前范围 | 2.3 fallback/cost/usage 治理 |
| Frontend | Vue 3 + API Types + Governance UI | 已验收当前范围 | 仅在 2.3 产品范围明确需要 UI 时扩展 |
| Browser E2E | Playwright Browser → Vue → Backend | 已验收当前范围 | 随 2.3 UI 链路裁剪执行 |

## 2. Phase 映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 2.1 | Enterprise Organization & Access Governance | 已关闭 | 否，除回归 |
| 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | **正式关闭** | 否，除回归 |
| **2.3** | **Model Provider Governance（路由/Fallback/成本/用量）** | **2.3-A/B 已实现，待本地 Gate** | **是** |
| 2.4 | Durable Scheduler | 候选路线 | 需求确认后 |
| 2.5 | Advanced Workflow Orchestration | 候选路线 | 需求确认后 |
| 2.6 | Enterprise Event Infrastructure | 候选路线 | 需求确认后 |
| 2.7 | Multi-Agent Collaboration | 候选路线 | 需求确认后 |
| 2.8 | Agent Asset / Marketplace | 候选路线 | 需求确认后 |

## 3. 2.3 Contract 与实现矩阵

| 能力 | Contract | 当前实现 | 验证 |
|---|---|---|---|
| Routing strategy | explicit_profile / organization_default | `model_provider_governance_contract.py` + routing API | Pending local tests |
| Fallback | transport failures only + max attempts 2 | Contract only；尚未接入 invocation loop | Pending |
| Model whitelist | capability + provider allowlist + model type | routing resolver 已实现 | Pending Real API |
| Cost | usage units + pricing source/version | Contract only；尚未持久化/计费 | Pending 2.3-C+ |
| Usage identity | organization/provider/profile/request/trace/outcome | Contract only；Runtime trace integration 待 2.3-C | Pending |

## 4. 当前产品完成判定

- P0：2.3-A/B 已有实际代码。
- P1：routing API Contract、权限与 scope 已定义。
- P2：unit + API Contract tests 已提交，**尚未由开发者本地执行**。
- P3：Real API **尚未执行本轮 2.3-B**。
- P4：本轮无新增 Frontend/Browser 链路，因此裁剪。
- P5：2.3-A/B 尚未 Acceptance 关闭。

## 5. 当前正式任务

**2.3-B Backend Domain + API Contract 已实现；下一任务为 2.3-C Runtime Routing Integration。**

2.3-C 必须：

1. 将 routing candidate 接入现有 `SessionService.load_runtime()` / `ModelGateway`。
2. 保持 organization/model_type/capability/profile identity 边界。
3. fallback 只处理 2.3-A 允许的失败原因。
4. 禁止回退到 Mock 来伪造真实 Provider 成功。
5. provider/profile/request/trace/outcome 写入现有 observability identity。
6. 若需要 pricing/usage 持久化，先 Migration。

## 6. Gate 顺序

```text
Targeted Contract Tests
→ Backend default regression
→ Migration/head verification（若有 migration）
→ Real API
→ Frontend/Browser（仅当 2.3-C 引入用户链路）
→ Acceptance / Status / Error Records
```

所有结果必须以开发者本地实际执行为准；未执行不得标记 Passed。
