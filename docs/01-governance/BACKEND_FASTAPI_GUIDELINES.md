# FastAPI + Python 后端通用项目开发准则

> **定位**：本文件定义基于 FastAPI + Python 的企业级后端项目通用工程规范，并进一步规定 Scheduler / Worker 服务及微服务架构的设计边界。可复制到其他 FastAPI 项目作为技术开发基线。
>
> 本文件遵循 `UNIVERSAL_DEVELOPMENT_GUIDELINES.md`。项目自身的 `DEVELOPMENT.md` 可以补充具体技术、目录、部署、CI 和测试环境，但不得无故违反核心工程原则。

---

## 1. 核心原则

1. **Contract First**：先定义 API / Event / Domain Contract，再实现业务。
2. **Domain First**：业务规则属于 Domain / Service，不属于 Router、ORM Model、Scheduler 或 Middleware。
3. **Dependency Direction**：业务依赖稳定抽象，Infrastructure 负责技术适配。
4. **Transaction Explicit**：事务边界必须明确，禁止隐式跨层事务。
5. **State as Fact**：持久化状态是业务事实，缓存、队列和内存状态不能无约束地成为第二事实源。
6. **Idempotency First**：所有可能重试、并发调用、异步消费的操作都必须定义幂等语义。
7. **Failure First**：Timeout、Retry、Conflict、Recovery、Partial Failure、Process Crash 都是正式设计的一部分。
8. **Security by Boundary**：Authentication、Authorization、Tenant Isolation、Secret 管理必须形成明确边界。
9. **Observable by Default**：关键请求、任务、消息、恢复和外部调用必须可关联到 Trace / Metrics / Logs。
10. **Service Boundary First**：微服务按业务能力和数据所有权拆分，而不是按技术文件或数据库表拆分。
11. **No Duplicate Capability**：同一能力只保留一个正式实现入口。

## 2. 推荐技术基线

```text
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2.x
Alembic
pytest
httpx
Redis（需要时）
Message Broker（需要异步解耦时）
uv / Poetry / pip-tools 等受控包管理方式
```

项目可以替换具体组件，但必须保持等价的 API、Validation、ORM、Migration、Test、Messaging 和 Observability 能力。

## 3. 推荐目录结构

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/<domain>/       # HTTP Router
│   ├── core/                  # 配置、安全、异常、日志
│   ├── dependencies/          # FastAPI DI / Request Context
│   ├── middleware/            # HTTP 横向处理
│   ├── models/                # ORM Model
│   ├── schemas/               # HTTP DTO / API Schema
│   ├── services/              # Domain Service
│   │   └── <domain>/
│   ├── runtime/               # 执行编排
│   ├── scheduler/             # 调度策略与调度循环
│   ├── worker/                # Worker 生命周期与执行入口
│   ├── messaging/             # Event / Command / Consumer / Publisher
│   ├── infrastructure/        # DB / Redis / Provider / HTTP / Broker
│   └── main.py
├── migrations/
├── scripts/
└── tests/
    ├── unit/
    ├── integration/
    ├── api_contract/
    ├── messaging/
    └── api_real/
```

复杂系统推荐将 Scheduler、Worker、API 做成独立可部署进程/服务，即使初期共享代码仓库，也必须保持运行时边界清晰。

## 4. 分层职责

```text
API / Consumer
      ↓
Application / Service
      ↓
Domain / Policy
      ↓
Runtime / Workflow
      ↓
Repository / Gateway
      ↓
Infrastructure
```

### API
负责 HTTP 边界、认证入口、Request Parsing、Response Serialization 和 Status Code。

### Consumer
负责消息反序列化、Schema 校验、Context 恢复、调用 Application Service，以及确认 Ack / Nack 策略。

### Scheduler
负责“**何时产生工作**”，不负责“**如何执行完整业务**”。

### Worker
负责“**领取并执行工作**”，不负责自行扫描全量调度规则。

### Service / Domain
负责业务规则、Policy、状态转换和持久化编排。

### Repository
负责持久化访问，不决定业务 Policy。

### Infrastructure
负责数据库、Redis、Broker、HTTP Client、Model Provider、Object Storage 等技术适配。

---

# 5. Scheduler / Worker 架构通用准则

## 5.1 核心职责边界

必须保持：

```text
Scheduler
  = Decide When

Queue / Broker
  = Transport Work

Worker
  = Execute Work

Runtime
  = Execute Steps

Repository / DB
  = Persist Facts

Recovery
  = Repair Interrupted Work
```

禁止 Scheduler 直接执行长时间业务任务，也禁止 Worker 自己决定调度全部任务。

## 5.2 推荐架构

```text
                    ┌───────────────┐
                    │   API Service │
                    └───────┬───────┘
                            │ Command
                            ▼
                    ┌───────────────┐
                    │  Domain / DB  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   Scheduler   │
                    │ Decide / Claim│
                    └───────┬───────┘
                            │ Job / Command
                            ▼
                    ┌───────────────┐
                    │ Queue / Broker │
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          Worker-1      Worker-2      Worker-N
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                    ┌───────────────┐
                    │ Execution     │
                    │ Runtime       │
                    └───────┬───────┘
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
              Database              Provider
```

## 5.3 Scheduler 不得做什么

Scheduler 禁止：

```text
❌ 直接执行 AI 推理
❌ 直接调用长耗时 Provider
❌ 执行复杂业务流程
❌ 持有业务执行状态的第二份副本
❌ 使用本地内存作为唯一调度事实
❌ 通过 sleep + 本地变量实现可靠任务队列
```

Scheduler 应只负责：

```text
读取可调度事实
→ 计算 Due
→ Claim / Lock
→ 创建 Job / Command
→ 投递 Broker
→ 记录调度结果
```

## 5.4 Scheduler 调度模型

推荐将调度设计成：

```text
Persistent Schedule
        ↓
Due Detection
        ↓
Atomic Claim
        ↓
Execution / Job Record
        ↓
Outbox / Publish
        ↓
Queue
```

不能使用：

```text
SELECT due rows
→ Python 判断
→ 多实例同时 INSERT
```

作为唯一并发保护。

必须通过数据库原子更新、唯一约束、Lease、分布式锁或等价机制解决竞争。

## 5.5 Scheduler 多实例

Scheduler 必须天然支持多实例部署：

```text
Scheduler A ─┐
Scheduler B ─┼─→ Atomic Claim → Job
Scheduler C ─┘
```

目标不是要求“只有一个 Scheduler”，而是：

> 多个 Scheduler 同时运行时，最终只有合法的一个调度结果进入执行链路。

如果业务允许重复投递，也必须由 Job / Worker 的幂等机制保证最终正确性。

## 5.6 Scheduler Tick

调度循环必须明确：

```text
poll interval
batch size
clock source
look-ahead window
misfire policy
backpressure
shutdown behavior
```

禁止无限制扫描全表。

推荐：

```text
Indexed Due Query
+ bounded batch
+ pagination / keyset
+ jitter
```

## 5.7 时间与时区

统一定义：

```text
Persist = UTC
Display = User / Tenant timezone
Schedule = Explicit timezone
```

必须考虑：

```text
DST
Leap Day
Clock Skew
Server Timezone
Misfire
```

业务 Scheduler 不得依赖服务器本地时区产生隐式行为。

## 5.8 Worker 生命周期

标准 Worker 生命周期：

```text
Start
 ↓
Load Config
 ↓
Connect Infrastructure
 ↓
Ready
 ↓
Consume / Claim
 ↓
Execute
 ↓
Heartbeat / Renew Lease
 ↓
Commit Result
 ↓
Ack
 ↓
Next Job
```

优雅停止：

```text
SIGTERM
 ↓
Stop Accepting New Work
 ↓
Finish / Checkpoint Safe Work
 ↓
Release / Expire Lease
 ↓
Close Connections
 ↓
Exit
```

禁止进程被终止时留下“永远执行中”的任务状态。

## 5.9 Job Claim

Worker 不能只读取任务：

```text
SELECT job
→ execute
```

必须先获得明确 ownership：

```text
Available
 ↓
Atomic Claim
 ↓
Running
 ↓
Lease / Owner
```

Claim 必须具有并发保护。

## 5.10 Lease

长任务推荐使用 Lease：

```text
owner_id
lease_id / fencing token
lease_expires_at
heartbeat_at
```

Worker 定期续租。

Lease 丢失后：

```text
Worker
 ↓
Stop protected execution
 ↓
Do not commit stale result
 ↓
Record lease-loss / recovery signal
```

禁止旧 Worker 在 Lease 失效后继续写入新的业务事实。

## 5.11 Fencing

仅有 Lease TTL 不足以防止网络分区后的旧 Worker 写入。

对于高价值状态更新，必须考虑 Fencing：

```text
Claim #101
   ↓
Fencing Token = 101

Reclaim
   ↓
Fencing Token = 102

Old Worker #101
   ↓
Write rejected
```

数据库写入必须验证 ownership / fencing token，而不能只验证“状态还是 running”。

## 5.12 Heartbeat

Heartbeat 必须区分：

```text
Worker Process Alive
        ≠
Worker Still Owns Job
```

Heartbeat 至少用于证明当前 Worker 仍拥有执行权。

Heartbeat 失败必须有明确策略：停止执行、进入安全状态或触发恢复；不得无限继续。

## 5.13 Queue / Broker

Queue 的职责是传输工作，不应成为业务最终事实源。

消息至少应携带：

```text
message_id
message_type
schema_version
job_id / execution_id
correlation_id
causation_id
created_at
tenant / context（按安全策略）
```

消费者必须允许消息重复投递。

## 5.14 Ack / Nack

推荐语义：

```text
成功完成并持久化结果
        ↓
ACK

临时失败，可重试
        ↓
NACK / Retry

永久失败
        ↓
Dead Letter / Failed State
```

不能在业务事实尚未可靠提交前提前 ACK。

## 5.15 Exactly Once

不要默认假设 Broker 能提供真正业务意义上的 Exactly Once。

工程目标通常应是：

```text
At-least-once delivery
+
Idempotent consumer
+
Atomic state transition
+
Transactional / reliable publication
```

## 5.16 Outbox / Inbox

当需要保证：

```text
DB Commit
+
Message Publish
```

的一致性时，推荐：

```text
Business Transaction
 ↓
DB State + Outbox Event
 ↓
Outbox Publisher
 ↓
Broker
```

消费者需要防重复处理时使用 Inbox / Processed Message 机制。

## 5.17 Retry

Worker Retry 必须明确：

```text
max attempts
backoff
jitter
retryable error
non-retryable error
retry deadline
```

禁止：

```text
except Exception
→ sleep
→ retry forever
```

## 5.18 Dead Letter

不可恢复消息必须进入明确的 Failed / DLQ 状态，并保留：

```text
message_id
job_id
attempt_count
error_code
error_summary
first_failed_at
last_failed_at
```

DLQ 必须具备人工或自动 Recovery 流程，不能成为永久垃圾桶。

## 5.19 Backpressure

Worker 系统必须有背压策略：

```text
Queue Depth
 ↓
Concurrency Limit
 ↓
Admission Control
 ↓
Rate Limit
```

禁止无限制增加 Worker 并发来解决积压。

必须保护：

```text
Database
Provider
CPU
Memory
External API quota
```

## 5.20 Poison Job

单个永远失败的 Job 不得阻塞整个队列。

应采用：

```text
Bounded Retry
→ Quarantine / DLQ
→ Alert
→ Recovery
```

## 5.21 Recovery

Recovery 是正式业务能力：

```text
Detect stale execution
 ↓
Validate ownership
 ↓
Classify failure
 ↓
Recover / Retry / Resume
 ↓
Record recovery trace
```

必须区分：

```text
Retry
Resume
Requeue
Compensate
Cancel
Manual Recovery
```

## 5.22 Checkpoint / Resume

长时间任务必须评估 Checkpoint：

```text
Execution
 ↓
Step completed
 ↓
Checkpoint
 ↓
Worker crash
 ↓
Resume from checkpoint
```

Checkpoint 必须是可验证的持久化事实，而不是 Worker 内存变量。

---

# 6. 微服务架构通用准则

## 6.1 微服务不是“拆几个 FastAPI 项目”

真正的微服务边界至少需要：

```text
Business Capability
+ Ownership
+ Contract
+ Data Boundary
+ Deployment Boundary
+ Failure Boundary
+ Scaling Boundary
```

如果两个服务必须共享同一套数据库事务才能完成一个简单操作，应首先重新评估服务边界。

## 6.2 服务拆分原则

优先按：

```text
Bounded Context
Business Capability
Data Ownership
Team Ownership
Scaling Characteristics
Failure Isolation
```

不要按：

```text
Controller Service
Utils Service
Database Service
Model Service
One-table-one-service
```

## 6.3 推荐微服务拓扑

```text
                    ┌───────────────┐
                    │ API Gateway   │
                    └───────┬───────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
       Identity        Domain A        Domain B
       Service         Service         Service
             │              │              │
             ▼              ▼              ▼
           DB-A           DB-A2           DB-B
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                       Event Broker
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
           Worker A     Worker B     Worker C
```

API Gateway 可以统一处理路由、认证入口、限流等，但不能成为所有业务逻辑的“大总管”。

## 6.4 Database per Service

推荐：

```text
Service A → DB A
Service B → DB B
```

服务之间禁止直接读取对方数据库表。

需要数据时通过：

```text
API
Event
Command
Read Model
Data Product
```

进行交换。

## 6.5 Shared Database 例外

早期单体或迁移阶段允许短期共享数据库，但必须：

```text
明确 Owner
明确访问边界
禁止跨服务直接修改对方表
制定迁移路线
```

不能因为共享数据库方便就永久维持隐式耦合。

## 6.6 同步调用 vs 异步事件

同步 API 适合：

```text
需要即时响应
查询
短事务
强一致交互
```

异步 Event / Command 适合：

```text
长任务
高吞吐
解耦
最终一致性
可靠后台执行
```

不要为了“微服务”把所有操作都异步化。

## 6.7 Event Contract

Event 必须版本化：

```text
Event Name
Schema Version
Producer
Consumer
Compatibility
Retention
```

Event 表示已经发生的事实，例如：

```text
OrderCreated
ExecutionCompleted
AgentRunFailed
```

Command 表示请求某个动作，例如：

```text
CreateOrder
ExecuteAgentRun
RebuildIndex
```

不要混淆 Event 与 Command。

## 6.8 API Versioning

公共 API 必须考虑：

```text
Backward Compatibility
Versioning
Deprecation
Migration Window
```

推荐优先兼容新增字段、可选字段，而不是频繁破坏旧 Contract。

## 6.9 Service-to-Service Authentication

服务间调用必须有独立身份：

```text
Service Identity
 ↓
Authentication
 ↓
Authorization
 ↓
Request
```

禁止所有服务共享一个超级 Token。

## 6.10 Service Discovery

服务地址必须通过：

```text
DNS
Service Registry
Orchestrator Service Discovery
```

解决。

禁止把生产 IP 硬编码进代码。

## 6.11 Resilience

微服务调用必须考虑：

```text
Timeout
Retry
Circuit Breaker
Bulkhead
Rate Limit
Fallback / Degradation
```

尤其禁止无限同步调用链：

```text
A → B → C → D → E
```

关键路径应控制依赖深度。

## 6.12 Distributed Transaction

默认不要跨微服务使用分布式数据库事务。

优先：

```text
Local Transaction
+
Outbox
+
Event
+
Saga / Compensation
```

需要跨服务一致性时，必须明确：

```text
Consistency Model
Failure State
Compensation
Timeout
Recovery
```

## 6.13 Saga

长事务可以采用：

```text
Step A
 ↓ Event
Step B
 ↓ Event
Step C
 ↓ Failure
Compensation B
 ↓
Compensation A
```

Saga 必须保证补偿操作幂等，并可从中间状态恢复。

## 6.14 Tenant Propagation

多租户微服务链路必须安全传播 Tenant Context：

```text
User Request
 ↓
Gateway
 ↓
Service A
 ↓ Event / API
Service B
 ↓
Worker
```

但下游服务必须验证调用身份及 Tenant 权限，不能盲目信任 Header 中的 `tenant_id`。

## 6.15 Correlation / Trace

跨服务必须传递：

```text
trace_id
span_id
correlation_id
causation_id
```

推荐：

```text
HTTP → Trace
Event → Trace Context
Job → Execution Context
Worker → Trace
```

最终形成完整链路：

```text
User
 ↓
API
 ↓
Service
 ↓
Event
 ↓
Scheduler
 ↓
Queue
 ↓
Worker
 ↓
Provider
```

## 6.16 Health / Readiness

必须区分：

```text
Liveness
= 进程是否还活着

Readiness
= 是否能够接收工作
```

Worker Ready 不等于 API Ready。

Scheduler Ready 也不等于 Scheduler 已经成功获得调度能力。

## 6.17 Graceful Shutdown

所有服务必须支持优雅退出：

```text
Stop accepting
 ↓
Drain
 ↓
Finish / checkpoint safe work
 ↓
Release resources
 ↓
Exit
```

Worker 尤其不能在收到 SIGTERM 后继续无限领取新 Job。

## 6.18 Deployment / Scaling

服务必须尽量无状态化：

```text
Instance 1
Instance 2
Instance N
```

状态放在：

```text
Database
Cache（非事实状态）
Broker
Object Storage
```

Scheduler 和 Worker 的扩缩容策略必须独立：

```text
Scheduler Scale
 = Schedule load

Worker Scale
 = Queue depth / execution load
```

## 6.19 Service Configuration

每个微服务必须拥有明确配置边界：

```text
SERVICE_NAME
ENVIRONMENT
DATABASE
BROKER
CACHE
TIMEOUT
CONCURRENCY
OBSERVABILITY
```

禁止读取其他服务的内部配置文件作为运行依赖。

## 6.20 Failure Isolation

一个服务故障不应自动拖垮全部服务。

必须识别：

```text
Critical dependency
Optional dependency
Async dependency
Fallback dependency
```

关键路径必须设置超时和隔离策略。

---

# 7. AI Agent 微服务专项架构

推荐：

```text
API Service
    ↓
Agent Orchestrator
    ↓
Execution / Runtime
    ↓
Queue
    ↓
Agent Worker
    ↓
Model / Tool Gateway
    ↓
External Systems
```

其中：

```text
Agent Orchestrator
= 创建和控制执行

Agent Worker
= 执行任务

Model Gateway
= 模型 Provider 适配

Tool Gateway
= 工具权限与执行边界
```

LLM 输出必须经过：

```text
Schema Validation
 ↓
Policy Validation
 ↓
Authorization
 ↓
Tool Execution
```

Prompt 不是权限系统。

---

# 8. 数据一致性原则

必须区分：

```text
Strong Consistency
Eventual Consistency
Read-after-write
At-least-once
Idempotent Processing
```

每个跨服务流程必须明确选择，而不是默认假设“最终都会一致”。

## 8.1 Source of Truth

每项业务事实必须明确 Owner：

```text
Execution State → Execution Service
Schedule → Scheduler / Scheduling Domain
User → Identity Service
Agent Definition → Agent Domain
```

其他服务只能保存：

```text
Cache
Projection
Read Model
Reference
```

不得与 Owner 同时成为事实写入方。

---

# 9. 测试体系

推荐：

```text
Unit
 ↓
Integration
 ↓
API Contract
 ↓
Messaging Contract
 ↓
Component / Service
 ↓
E2E
 ↓
Failure / Recovery Test
```

Scheduler / Worker 必须额外测试：

```text
Duplicate Schedule
Concurrent Claim
Lease Expiry
Heartbeat Failure
Worker Crash
Message Redelivery
Retry Exhaustion
DLQ
Recovery
Graceful Shutdown
```

微服务必须测试：

```text
Contract Compatibility
Service Timeout
Dependency Failure
Network Failure
Partial Failure
Event Version Compatibility
```

## 9.1 不稳定测试禁止

测试不得依赖：

```text
真实时间睡眠
随机网络
共享测试数据库状态
未清理队列
不确定的并发时序
```

需要测试时间时使用 Clock abstraction / fake time；需要测试并发时使用明确的 synchronization barrier。

---

# 10. Observability

Scheduler 指标至少包含：

```text
schedule_scan_count
schedule_claim_count
schedule_duplicate_prevented
schedule_publish_count
schedule_misfire_count
```

Worker 指标至少包含：

```text
job_received
job_claimed
job_completed
job_failed
job_retried
job_dlq
job_duration
lease_lost
recovery_count
```

微服务指标至少包含：

```text
request_rate
error_rate
latency
queue_depth
dependency_latency
circuit_breaker_state
```

日志必须能够从：

```text
request_id
trace_id
correlation_id
job_id
execution_id
message_id
```

关联到完整执行链路。

---

# 11. 安全准则

禁止：

```text
❌ 服务共享超级凭据
❌ 客户端 tenant_id 直接决定权限
❌ Worker 使用不受限数据库账号
❌ Scheduler 使用业务超级权限
❌ Token / Secret 写日志
❌ 将 Prompt 当权限系统
❌ Event 中无约束携带敏感数据
```

推荐最小权限：

```text
API → 业务所需权限
Scheduler → 调度所需权限
Worker → 执行所需权限
Publisher → 发布所需权限
Consumer → 消费所需权限
```

---

# 12. 性能与容量设计

所有 Scheduler / Worker 服务必须在上线前回答：

```text
Expected QPS
Expected jobs/sec
Average job duration
P95 / P99 duration
Max concurrency
Queue capacity
DB connection capacity
Provider rate limit
Recovery load
```

容量估算必须同时考虑：

```text
Normal Load
Peak Load
Retry Storm
Recovery Storm
Provider Degradation
```

Worker 并发不能超过下游系统可承受能力。

---

# 13. 新增 Scheduler / Worker 功能标准流程

```text
① 阅读项目 DEVELOPMENT.md
② 同步最新代码
③ 确认 Domain / Contract / State
④ 明确 Scheduler / Queue / Worker / Runtime 边界
⑤ 定义 Job / Event / Command Schema
⑥ 定义 Claim / Lease / Ownership
⑦ 定义 Idempotency
⑧ 定义 Retry / DLQ / Recovery
⑨ 定义 Transaction / Outbox（需要时）
⑩ 实现 Domain
⑪ 实现 Scheduler
⑫ 实现 Consumer / Worker
⑬ 实现 Runtime
⑭ 添加 Metrics / Trace / Logs
⑮ Unit Test
⑯ Integration / Messaging Test
⑰ Failure / Recovery Test
⑱ Load Test（关键链路）
⑲ 更新 Architecture / Status / Acceptance
⑳ Commit / Review
```

---

# 14. 新增微服务标准流程

```text
① 判断是否真的需要服务拆分
② 定义 Bounded Context
③ 定义 Business Capability
④ 确定 Data Owner
⑤ 定义 API / Event / Command Contract
⑥ 定义同步 / 异步边界
⑦ 定义 Authentication / Authorization
⑧ 定义 Tenant Context
⑨ 定义 Timeout / Retry / Circuit Breaker
⑩ 定义 Failure / Recovery
⑪ 定义 Trace / Metrics / Logs
⑫ 建立 Service
⑬ 建立独立测试
⑭ Contract Test
⑮ Failure Test
⑯ 部署与扩缩容验证
⑰ 文档 / Acceptance
```

---

# 15. Definition of Done

## Scheduler

```text
[ ] 多实例安全
[ ] Due Query 有索引
[ ] Atomic Claim
[ ] Duplicate Prevention
[ ] Misfire Policy
[ ] Backpressure
[ ] Graceful Shutdown
[ ] Metrics / Trace
```

## Worker

```text
[ ] Atomic Claim
[ ] Lease
[ ] Heartbeat
[ ] Fencing（适用时）
[ ] Idempotency
[ ] Timeout
[ ] Retry
[ ] DLQ
[ ] Recovery
[ ] Checkpoint（长任务适用）
[ ] Graceful Shutdown
[ ] Metrics / Trace
```

## Microservice

```text
[ ] Bounded Context
[ ] Business Capability
[ ] Data Ownership
[ ] API / Event Contract
[ ] Versioning
[ ] Authentication
[ ] Authorization
[ ] Tenant Isolation
[ ] Timeout / Retry
[ ] Failure Isolation
[ ] Observability
[ ] Independent Deployment
[ ] Independent Scaling
[ ] Contract Tests
[ ] Recovery Strategy
```

---

# 16. 后端通用 Definition of Done

```text
[ ] Domain boundary clear
[ ] API / Event Contract defined
[ ] Authorization considered
[ ] Tenant isolation considered
[ ] State transition defined
[ ] Idempotency defined
[ ] Transaction boundary defined
[ ] Timeout / Retry defined
[ ] Error Contract defined
[ ] Migration completed（需要时）
[ ] Scheduler / Worker semantics defined（需要时）
[ ] Failure / Recovery defined
[ ] Observability added
[ ] Unit tests
[ ] Integration / Contract tests（适用时）
[ ] No secret leakage
[ ] No duplicate implementation
[ ] Documentation updated
[ ] Git change traceable
```

# 17. 禁止事项

```text
❌ Router 承载核心业务逻辑
❌ ORM Model 直接作为公开 Contract
❌ Repository 决定业务 Policy
❌ Scheduler 直接执行长任务
❌ Worker 无 Claim 直接执行 Job
❌ Lease 失效后继续写业务事实
❌ Queue 消息默认假设 Exactly-once
❌ 无界 Retry
❌ 无 DLQ 的永久失败消息
❌ DB Commit 与 Event Publish 无一致性设计
❌ 服务直接读取其他服务数据库
❌ 所有服务共享超级凭据
❌ 通过 sleep + 内存状态实现可靠调度
❌ BackgroundTasks 冒充 Durable Queue
❌ Cache 成为未经定义的第二事实源
❌ except Exception 后吞异常
❌ Secret / Token 写入日志或代码
❌ 只测试成功路径
❌ 用兼容层掩盖重构未完成
❌ 未测量的性能优化

---

# 18. 与项目治理文档的关系

```text
UNIVERSAL_DEVELOPMENT_GUIDELINES.md
            ↓
FastAPI + Python 通用准则
            ↓
Scheduler / Worker / Microservice Guidelines
            ↓
项目 DEVELOPMENT.md
            ↓
Architecture / Domain Design
            ↓
Implementation
            ↓
Test Gate
            ↓
Acceptance
```

本文件解决“FastAPI + Python 后端如何工程化，以及如何构建可靠 Scheduler / Worker 和微服务”；具体项目负责补充实际数据库、Broker、部署平台、CI/CD、命令和运行参数。