# LT-01 Enterprise Integration / Event Infrastructure

## 1. 目标
建立可靠、可治理、可观测的企业系统集成与事件基础设施，使 Agent、Workflow、Scheduler、Delegation 能与外部业务系统形成稳定异步协作。

## 2. 当前状态
**待立项 / Contract 前置评估。** 当前已有 Webhook/Trigger、Audit、Trace 等能力，但尚不能据此认定已经形成完整企业级 Event Infrastructure。

## 3. 主要缺口
- 统一 Event / Integration Contract；
- Event identity、幂等键、版本与 schema 演进；
- 投递语义、重试、退避、死信和失败恢复；
- 顺序性、并发、租户隔离；
- Outbox/消息中间件是否需要的架构决策；
- Webhook endpoint、签名、安全与回放；
- Event tracing、delivery audit、运营查询；
- 与 Workflow/Agent Runtime 的可靠衔接。

## 4. 长期拆解
1. 盘点现有 Event/Webhook/Trigger/Audit/Trace/Outbox 实现；
2. 定义业务事件模型与 Integration Contract；
3. 定义可靠投递、幂等、顺序和失败语义；
4. 决策数据库 Outbox、消息队列或其他实现边界；
5. 实现统一 Integration Domain；
6. 接入 Workflow/Agent/Scheduler；
7. 建立 Real API 与故障恢复验收。

## 5. 完成判定
Contract 冻结、唯一正式实现入口、Migration（如需要）、Unit/Integration/Contract/Real API 验收完整，并具备失败重试、幂等、隔离和可观测证据。

## 6. 明确不做
在 Contract 冻结前不得直接引入 Kafka、MQ、Event Bus 或第二套 Outbox；不得复制现有 Webhook/Trigger/Trace 能力。
