# LT-06 Security / Secrets / Policy

## 1. 目标
建立企业级 AI Agent 安全基线，覆盖 Secret、策略、工具调用、数据访问、模型调用和高风险操作。

## 2. 当前状态
**待立项。** 当前已有 Tenant/RBAC/Audit/Provider Governance 等安全基础，但完整企业安全控制面尚未完成。

## 3. 主要缺口
- Secret vault / credential lifecycle；
- Secret rotation；
- Policy engine；
- Tool permission / network egress policy；
- Prompt/data access boundary；
- PII/data classification 与脱敏；
- 高风险 Agent 操作审批；
- 安全事件审计；
- 安全配置与合规基线。

## 4. 长期拆解
Threat model → Secret Contract → Policy model → Runtime enforcement → Data protection → Approval/audit → Security test → Compliance evidence。

## 5. 完成判定
Secret 不落代码/日志，关键 Agent/Tool/Provider 操作可受策略约束，跨 Tenant 访问被可靠阻断，安全测试与审计证据完整。
