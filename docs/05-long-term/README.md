# 长期任务记录

> 本目录只记录当前未完成、需要跨 Phase 持续推进的长期产品/工程能力。
> 长期任务与 `docs/02-phases/` 的当前阶段计划严格分离；不得把长期任务的未完成项直接当作当前 Phase 的开发任务。

## 管理原则

- 每项长期能力一个独立文档。
- LT 文档记录目标、现状、缺口、边界、依赖、阶段性里程碑和完成判定。
- 已关闭 Phase 不因长期任务而重新打开；已验收 Runtime 只保留回归维护。
- LT 状态只能在真实代码、测试和验收证据发生变化后更新。
- 候选技术不得在 Contract 冻结前写成既定实现方案。
- 真正进入正式开发时，再建立对应 `docs/02-phases/PHASE_x_y.md`。

## 当前长期任务

| ID | 能力 | 当前状态 | 说明 |
|---|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | **Phase 2.9 开发中** | 已完成统一 Event Contract 第一切片，后续进入 Durable Event Persistence |
| LT-02 | Enterprise IAM / SSO / Identity Federation | 待立项 | 从现有 Tenant/RBAC 向企业身份体系扩展 |
| LT-03 | Enterprise Operations Console | 待立项 | 完整运营、任务、Worker、Scheduler、故障处理控制台 |
| LT-04 | API / Developer Platform | 待立项 | API 生命周期、SDK、Webhook、凭证、开发者治理 |
| LT-05 | Observability / SRE | 待立项 | 指标、告警、SLO、分布式追踪、容量与运行诊断 |
| LT-06 | Security / Secrets / Policy | 待立项 | Secret、策略、审批、数据安全、运行时安全边界 |
| LT-07 | Agent Evaluation / Quality | 待立项 | 离线评测、在线质量、回归集、人工反馈与版本质量门禁 |
| LT-08 | Cost / Quota / Billing | 待立项 | 资源配额、成本中心、预算、计量与计费能力 |
| LT-09 | Agent Asset / Marketplace | 候选 | Agent/Workflow/Tool/Prompt 等资产生命周期与共享治理 |
| LT-10 | Production Deployment / HA / Operations | 待立项 | 生产部署、HA、扩缩容、灾备、升级与运维自动化 |

## 与当前 Phase 的关系

当前 `main` 已完成 Phase 2.8 Multi-Agent Collaboration Runtime Integration，并已正式进入 Phase 2.9 Enterprise Integration / Event Infrastructure。

LT-01 仍负责记录长期企业集成能力的完整缺口；Phase 2.9 只承接其中已经冻结并进入实现的工作。当前第一切片为统一 Event Contract，下一切片为 Durable Event Persistence。

除非对应 Phase 有真实代码、测试和验收证据，其他 LT 项目仍保持“待立项”，不得提前写成开发中。
