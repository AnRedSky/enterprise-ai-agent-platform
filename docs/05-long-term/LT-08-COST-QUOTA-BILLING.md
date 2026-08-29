# LT-08 Cost / Quota / Billing

## 1. 目标
在现有 Provider usage/cost accounting 基础上形成企业级资源计量、配额、预算和计费体系。

## 2. 当前状态
**待立项。** 当前已有 Provider Governance 与 durable usage/cost accounting，可作为长期任务基础，但尚不是完整 Billing 平台。

## 3. 主要缺口
- Tenant/Organization/Project quota；
- Token、模型、Tool、Workflow、Runtime resource metering；
- Budget 与 spend limit；
- Cost allocation；
- 预警与超额策略；
- 价格表/费率版本；
- Invoice/billing export；
- 计量数据校验、补偿和审计。

## 4. 长期拆解
Metering Contract → Quota → Budget → Pricing/versioning → Cost allocation → Alert/enforcement → Billing export → Audit。

## 5. 完成判定
资源消耗可准确、可追溯计量；配额和预算可强制执行；价格与账单数据可版本化、审计并导出。
