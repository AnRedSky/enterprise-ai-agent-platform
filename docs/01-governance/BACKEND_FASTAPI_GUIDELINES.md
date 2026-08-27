# FastAPI + Python 后端通用项目开发准则

> **定位**：本文件是可复用的 FastAPI + Python 后端技术开发基线，不针对任何单一业务项目。它规定工程原则、分层、横向基础能力、异步任务、Scheduler / Worker、微服务、测试、部署与演进规则。具体项目可选择其中能力，并在项目级 `DEVELOPMENT.md` 中确定实际技术组件与目录。

## 1. 适用范围与核心原则

1. **Contract First**：先定义 API / Event / Command / Domain Contract，再实现。
2. **Separation of Concerns**：API、Application、Domain、Infrastructure、Runtime 各司其职。
3. **Dependency Direction**：业务依赖稳定抽象，基础设施实现抽象。
4. **Explicit Transaction**：事务边界明确，不允许隐式跨层事务。
5. **State as Fact**：数据库或明确的事实存储是状态权威；缓存、队列、内存不是未经设计的第二事实源。
6. **Idempotency First**：所有重试、并发、异步消费和可恢复操作必须定义幂等语义。
7. **Failure First**：Timeout、Retry、Conflict、Crash、Partial Failure、Recovery 都必须进入设计。
8. **Security by Boundary**：认证、授权、凭据、租户隔离和敏感数据保护形成明确边界。
9. **Observable by Default**：关键请求、任务、消息和外部调用必须可关联。
10. **Service Boundary First**：微服务按业务能力、数据所有权和独立演进需求拆分。
11. **No Duplicate Capability**：同一基础能力只能有一个正式实现入口。
12. **Prefer Simple Architecture**：没有明确收益时优先模块化单体，不为了微服务而微服务。

## 2. 技术基线

推荐：

```text
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2.x
Alembic
pytest
httpx
```

Redis、消息 Broker、任务队列、Tracing、Metrics 等按项目需要启用。项目可以替换具体组件，但必须保留等价能力。

## 3. 推荐目录与组织原则

目录结构只作为推荐，不作为所有项目的强制模板。必须满足职责边界和依赖方向。

```text
backend/
├── app/
│   ├── api/                  # API 接入
│   ├── application/          # 用例编排
│   ├── domain/               # 业务规则
│   ├── infrastructure/       # 外部技术实现
│   ├── schemas/               # DTO / Contract
│   ├── runtime/               # 可持续执行能力（需要时）
│   ├── scheduler/             # 调度能力（需要时）
│   ├── worker/                # 异步执行能力（需要时）
│   ├── core/                  # 应用级横向核心能力
│   ├── common/                # 跨模块稳定共享定义
│   └── utils/                 # 纯技术辅助函数
├── migrations/
├── scripts/
└── tests/
```

### 3.1 Core / Common / Utils 边界

为避免顶级目录过多，以下能力可以统一收敛到 `core/`：

```text
core/
├── config/                    # 类型化配置、环境、Secret 接入、启动校验
├── security/                  # Authentication / Authorization / Credential / Tenant
├── errors/                    # Error Code / Exception / Handler / Response Mapping
├── observability/             # Logging / Metrics / Tracing / Audit / Correlation
├── lifecycle/                 # Startup / Shutdown / Health / Readiness
└── context/                   # Request / Tenant / Execution / Correlation Context
```

`core` 的定义是**应用级核心运行能力**，不是业务代码垃圾桶。业务 Service、Repository、Provider、Scheduler、Worker 不得因为“大家都用”而进入 Core。

`common/` 只放跨多个模块共享且稳定、低业务耦合的定义：

```text
common/
├── types/
├── enums/
├── constants/
└── protocols/
```

`common` 不得承载业务 Service、业务 Entity、Repository 实现或业务 Policy。只服务一个 Domain 的定义应留在该 Domain。

`utils/` 只允许无状态、低副作用、无业务语义的纯技术辅助函数，例如日期、编码、哈希、序列化和文本处理。禁止 `utils/user.py`、`utils/order.py`、`utils/service.py` 等业务工具。

### 3.2 目录判断原则

```text
整个应用运行都可能依赖？        → core
多个模块共享的稳定定义？        → common
纯技术、无业务语义的辅助函数？  → utils
业务规则？                      → domain
业务用例编排？                  → application
外部技术实现？                  → infrastructure
持续执行 / 恢复？               → runtime
调度触发？                      → scheduler
异步任务执行？                  → worker
HTTP 接入？                     → api
```

目录可以调整，但不得通过目录名称掩盖职责错误。

## 4. 分层与依赖

推荐：

```text
API / Consumer
      ↓
Application
      ↓
Domain
      ↓
Infrastructure
```

横向能力由 `core/common` 提供稳定 Contract；具体数据库、缓存、消息、HTTP、Provider 等实现属于 Infrastructure。

禁止：

```text
Domain ─X→ FastAPI
Domain ─X→ ORM
Domain ─X→ Redis
Domain ─X→ Provider SDK
Domain ─X→ HTTP Request
```

外部能力必须通过 Port / Protocol / Interface 隔离。

## 5. Configuration

配置必须：

- 集中管理；
- 类型化；
- 启动校验；
- 区分环境配置与 Secret；
- 支持安全的环境覆盖；
- 默认禁止运行期间任意修改关键配置。

禁止业务代码散落 `os.getenv()`、Secret 文件读取和配置解析。

## 6. Security

安全能力至少覆盖：

```text
Authentication
Authorization
Credential / Secret Management
Tenant Isolation（需要时）
Input Validation
Sensitive Data Protection
Security Audit
```

认证解决“是谁”，授权解决“能做什么”，资源隔离解决“能访问哪些数据”。业务代码不得直接耦合具体 JWT、Session 或 HTTP Header 实现。

## 7. Error Handling

错误至少分为：

```text
Validation
Authentication
Authorization
Domain
Application
Conflict
Infrastructure
Timeout
Internal
```

要求：稳定 Error Code、明确错误分类、统一响应 Contract、正确 HTTP 状态映射、保留诊断上下文且不得泄露 Secret / PII。

不要使用裸 `except Exception` 吞掉错误；异常必须被记录、转换、重试或向上交由统一处理器。

## 8. Logging & Observability

推荐统一进入：

```text
core/observability/
├── logging/
├── metrics/
├── tracing/
├── audit/
└── correlation/
```

日志应结构化，并尽量包含：

```text
timestamp
severity
service
operation
request_id
trace_id
correlation_id
user / tenant context（按安全策略）
```

禁止日志输出 Token、密码、完整 Secret 和不必要的敏感数据。

## 9. API & Contract

API 必须明确：

```text
Request Schema
Response Schema
Error Schema
Version
Authentication
Authorization
Idempotency
Pagination
Filtering / Sorting
```

不要让 ORM Model 直接成为稳定的公开 API Contract。破坏性变更必须有版本、迁移或兼容策略。

## 10. Data & Transaction

- Repository 负责数据访问，不决定业务 Policy。
- Transaction Boundary 必须明确。
- Migration 必须版本化、可重复验证。
- 索引必须根据真实查询设计。
- 不能依赖 ORM 默认行为理解事务。
- 跨服务事务不得依赖共享数据库事务；需要时使用 Saga、Outbox 等模式。

## 11. Concurrency & Idempotency

任何可能发生：

```text
Concurrent Request
Retry
Duplicate Message
Worker Crash
Timeout + Unknown Result
```

的操作，都必须定义并发和幂等策略。

优先使用数据库唯一约束、原子更新、版本号、Lease、Idempotency Key 等机制，而不是依赖 Python 内存锁。

## 12. Async / Background Processing

后台任务是可选能力。简单、短生命周期任务可以使用框架能力；可靠、可重试、跨进程、长耗时任务应使用持久化 Job + Queue/Broker + Worker 等架构。

通用职责：

```text
Scheduler = Decide When
Queue     = Transport Work
Worker    = Execute Work
Runtime   = Execute Steps（需要时）
Recovery  = Repair Interrupted Work
```

不要把可靠任务放在进程内存中作为唯一事实。

# 13. Scheduler 通用架构

Scheduler 不是业务执行器。它负责发现到期工作、创建 Job/Command 并可靠投递。

推荐：

```text
Persistent Schedule
      ↓
Due Detection
      ↓
Atomic Claim
      ↓
Job / Command
      ↓
Outbox / Publish
      ↓
Queue
```

必须定义：

```text
poll interval
batch size
clock source
timezone
misfire policy
backpressure
shutdown behavior
```

多实例 Scheduler 必须使用数据库原子条件、唯一约束、Lease、分布式协调或等价机制避免重复调度。

时间持久化通常采用 UTC；业务计划必须显式保存时区，并处理 DST、Clock Skew、Misfire 等问题。

Scheduler 禁止直接执行长耗时业务、调用高延迟 Provider、扫描全表后依赖本地判断作为唯一并发保护。

## 14. Worker 通用架构

Worker 负责领取并执行 Job：

```text
Consume / Claim
      ↓
Ownership
      ↓
Lease / Fencing（长任务或高价值状态需要时）
      ↓
Execute
      ↓
Checkpoint（需要时）
      ↓
Commit
      ↓
ACK
```

必须考虑：

```text
Graceful Shutdown
Retry
Timeout
Backpressure
Dead Letter
Poison Job
Recovery
Idempotent Consumer
```

### 14.1 Lease

长任务使用 Lease 时应记录 Owner、Lease Expiration、Heartbeat，必要时使用 Fencing Token。Lease 失效后旧 Worker 不得继续提交受保护业务事实。

### 14.2 ACK / Retry

只有业务事实可靠提交后才 ACK。临时错误采用有界重试 + Backoff + Jitter；永久错误进入 Failed / DLQ。禁止无限重试。

### 14.3 At-least-once

不要假设消息系统提供业务意义上的 Exactly-once。默认设计目标应是：

```text
At-least-once
+
Idempotent Consumer
+
Atomic State Transition
+
Reliable Publication
```

## 15. Outbox / Inbox

需要保证数据库状态与消息发布一致时：

```text
Business Transaction
 ↓
DB State + Outbox
 ↓
Publisher
 ↓
Broker
```

需要防止重复消费时采用 Inbox / Processed Message / Idempotency Record 等机制。

## 16. Recovery / Checkpoint

长时间或高价值任务应评估 Checkpoint：

```text
Step Complete
 ↓
Checkpoint
 ↓
Crash
 ↓
Recover
 ↓
Resume / Retry / Compensate
```

Recovery 必须区分 Retry、Resume、Requeue、Compensate、Cancel、Manual Recovery。

## 17. Microservice Architecture

微服务是可选架构，不是默认要求。

推荐演进：

```text
Modular Monolith
      ↓
明确业务边界 / 数据所有权 / 独立扩缩容需求
      ↓
Service Extraction
      ↓
Microservices
```

拆分依据：

```text
Business Capability
Bounded Context
Data Ownership
Team Ownership
Deployment Independence
Scaling Boundary
Failure Isolation
Security Boundary
```

禁止按 Controller、ORM Table、文件类型机械拆服务。

### 17.1 Service Contract

服务间只能通过明确的：

```text
REST / HTTP
RPC
Event
Command
```

进行交互。Contract 必须版本化、可测试、可演进。

### 17.2 Service Data Ownership

默认每个服务拥有自己的业务数据；禁止多个服务直接修改同一业务表。跨服务数据通过 API、Event、Read Model 或明确的同步机制交换。

### 17.3 Service Resilience

服务间调用必须定义：

```text
Timeout
Retry Policy
Circuit Breaker（需要时）
Rate Limit
Bulkhead / Concurrency Limit
Fallback（有业务意义时）
```

禁止无限超时、无限重试和级联失败。

### 17.4 Distributed Transaction

禁止把跨服务一致性建立在共享数据库事务上。根据业务一致性要求选择 Saga、Compensation、Outbox、Eventual Consistency 等机制。

## 18. External Integration

第三方 SDK、LLM、支付、邮件、存储、HTTP API 等必须通过 Gateway / Adapter 隔离。

业务代码依赖：

```text
Provider Contract
```

而不是直接依赖：

```text
Vendor SDK
```

外部调用必须定义 Timeout、Retry、错误映射、限流、日志脱敏和可观测性。

## 19. Testing

最低要求按项目风险选择：

```text
Unit
Integration
API Contract
Database
Messaging（使用时）
End-to-End（关键流程）
```

Scheduler / Worker 项目必须额外测试：

```text
Duplicate Delivery
Concurrent Claim
Lease Expiration
Worker Crash
Retry
DLQ
Recovery
Graceful Shutdown
```

测试不得依赖真实生产 Secret、生产数据库或不可控外部服务。

## 20. Performance

优化顺序：

```text
Measure
 ↓
Identify Bottleneck
 ↓
Optimize
 ↓
Benchmark
 ↓
Observe Regression
```

重点关注：DB Query、Connection Pool、External I/O、Serialization、Concurrency、Queue Latency、Memory。

禁止没有指标依据的过早优化。

## 21. Deployment & Runtime

服务必须支持：

```text
Configuration Injection
Health Check
Readiness
Graceful Shutdown
Structured Logs
Metrics / Tracing（按项目要求）
```

API、Scheduler、Worker 如需要不同资源模型，应独立进程部署；是否独立容器/服务由项目实际规模决定。

## 22. Code Quality

要求：

- 类型注解优先；
- 明确函数输入输出；
- 小函数、单一职责；
- 避免隐式全局状态；
- 不复制相同业务逻辑；
- 复杂逻辑必须有测试和说明；
- 依赖方向必须可审查。

格式化、Lint、Type Check、Test 必须纳入 CI Quality Gate。

## 23. Documentation

至少维护：

```text
Architecture
API Contract
Configuration
Deployment
Database Migration
Error Contract
Operational Runbook（需要时）
```

文档必须描述当前真实实现，不允许以过时架构图代替代码事实。

## 24. Definition of Done

一个后端功能完成前至少确认：

```text
[ ] Contract 明确
[ ] 分层正确
[ ] 权限 / 安全完成
[ ] Error Contract 完成
[ ] Transaction 明确
[ ] Idempotency 明确（需要时）
[ ] Logging / Metrics / Trace 完成（按风险）
[ ] Tests 完成
[ ] Migration 完成（需要时）
[ ] Timeout / Retry 完成（需要时）
[ ] Documentation 更新
[ ] CI Quality Gate 通过
```

## 25. 禁止事项

```text
❌ Router 承载业务逻辑
❌ ORM Model 直接作为长期 API Contract
❌ Domain 直接依赖 Infrastructure
❌ 把业务 Service 放进 common / utils / core
❌ 把所有异常吞掉
❌ 无限 Retry
❌ 本地内存作为可靠任务事实源
❌ Scheduler 直接执行长耗时业务
❌ Worker 扫描全部调度规则
❌ 无边界的共享数据库写入
❌ 为了微服务而微服务
❌ 为了“目录统一”强制所有项目采用同一目录
```

## 26. 与项目级开发准则的关系

本文件是**技术栈通用基线**。具体项目的 `DEVELOPMENT.md` 可以决定：

```text
实际目录
数据库
Cache
Broker
Scheduler
Worker
Service Boundary
部署方式
CI/CD
测试命令
```

但项目级规则不应无故破坏本文件定义的职责边界、可靠性、安全性和可维护性原则。
