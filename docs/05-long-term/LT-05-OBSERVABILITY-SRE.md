# LT-05 Observability / SRE

## 1. 目标
将当前 Execution/Event/Trace/Audit 可观测能力提升为企业生产级 Observability 与 SRE 体系。

## 2. 当前状态
**待立项。** 当前已有日志、Execution、Trace、Audit 及部分 UI/治理能力，但尚不足以认定具备完整 SRE 能力。

## 3. 主要缺口
- Metrics 指标体系；
- RED/USE 等服务与资源指标；
- SLI/SLO/SLA；
- 告警规则与通知；
- 分布式 Trace correlation；
- Worker/Scheduler/Queue/DB runtime telemetry；
- 容量与性能基线；
- incident diagnosis/runbook；
- 数据保留、采样和多租户可见性。

## 4. 长期拆解
Telemetry contract → Metrics → Trace correlation → SLO/Alert → Capacity baseline → Incident workflow → Operations integration → Load/Failure validation。

## 5. 完成判定
关键链路具有可查询指标、Trace、SLO、告警和故障诊断路径，并可在真实运行环境验证。
