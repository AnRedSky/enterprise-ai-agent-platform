# FastAPI + Python 后端通用项目开发准则

> **定位**：本文件是可复用的 FastAPI + Python 后端技术开发基线。本文基于既有后端目录架构补充和细化 `core/`、`common/`、`utils/` 的职责，不推翻既有目录层次，也不要求其他项目机械复制全部目录。通用原则优先于目录名称；目录用于表达职责边界。

## 1. 适用范围与核心原则

1. **Contract First**：先定义 API / Event / Command / Domain Contract，再实现。
2. **Separation of Concerns**：API、Service、Domain Model、Infrastructure、Runtime 各司其职。
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
13. **Existing Structure First**：对已有项目进行规范化时优先增量治理和职责收敛，不因目录美化进行无收益的大规模搬迁。

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

目录结构用于表达职责边界。对于已有项目，优先在现有结构内完善模块，不应为了追求理论上的目录纯度而整体迁移。

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/<domain>/       # HTTP Router / API 接入
│   ├── core/                  # 配置、安全、异常、日志等应用级核心能力
│   ├── dependencies/          # FastAPI DI / Request Context
│   ├── middleware/            # HTTP 横向处理
│   ├── models/                # ORM Model / Persistence Model
│   ├── schemas/               # HTTP DTO / API Schema
│   ├── services/              # Domain / Application Service
│   │   └── <domain>/
│   ├── runtime/               # 执行编排 / 状态运行时（需要时）
│   ├── scheduler/             # 调度策略与调度循环（需要时）
│   ├── worker/                # Worker 生命周期与执行入口（需要时）
│   ├── messaging/             # Event / Command / Consumer / Publisher（需要时）
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

### 3.1 Core / Common / Utils 的定位

为了保持顶层目录清晰，`core/`、`common/`、`utils/` 可以承载横向基础能力，但三者职责必须严格区分：

```text
core/
    应用级核心运行能力

common/
    跨模块稳定共享定义

utils/
    无状态、纯技术、低耦合辅助函数
```

它们都不是“只要很多地方使用就可以放进去”的万能目录。

---

## 3.2 Core：应用级核心能力

### 定义

`core/` 用于承载**整个应用运行过程中具有基础性、横向性、生命周期性，但不属于具体业务 Domain 的核心能力**。

推荐结构：

```text
core/
├── config/                    # 配置、环境、Secret 接入、启动校验
├── security/                  # Authentication / Authorization / Credential
├── exceptions/                # Exception 基类、错误分类、错误码
├── logging/                   # 结构化日志与日志上下文
├── observability/             # Metrics / Tracing / Audit / Correlation（规模需要时）
├── lifecycle/                 # Startup / Shutdown / Health / Readiness
├── context/                   # Request / Tenant / Execution Context
└── constants.py               # 仅限应用级、非业务常量（可选）
```

`exceptions/` 与 `logging/` 可以继续保留为独立 Core 子模块；当项目需要更完整的可观测性时，可以在 Core 内进一步形成 `observability/`，而不是新增大量顶级目录。

### Core 允许承担的职责

```text
配置加载与校验
应用生命周期
认证与授权基础设施
统一异常模型
结构化日志
Trace / Metric / Audit 基础能力
请求 / 租户 / 执行上下文
基础依赖注册
健康检查与就绪检查
```

### Core 禁止承担的职责

```text
业务 Service
业务 Entity
业务 Repository
ORM Model
第三方 Provider 实现
具体数据库访问
具体 Redis 业务操作
Scheduler 业务逻辑
Worker 业务逻辑
API Router
```

判断标准：

> 如果删除某个业务 Domain 后，该代码仍然有完整意义，它才可能属于 Core；如果它表达的是某个业务对象、业务规则或业务流程，就不应进入 Core。

---

## 3.3 Core / Config

推荐：

```text
core/config/
├── settings.py                # 类型化配置模型
├── environment.py             # 环境识别与环境策略
├── secrets.py                 # Secret 接入抽象
└── validation.py              # 启动配置校验
```

要求：

- 配置集中管理；
- 配置类型化；
- 启动阶段完成关键校验；
- Secret 与普通配置分离；
- 支持开发、测试、生产环境差异；
- 关键运行配置默认不可被业务代码随意修改。

禁止：

```python
os.getenv("SOME_CONFIG")
```

散落在 Service、Router、Repository、Worker 等业务代码中。

---

## 3.4 Core / Security

推荐：

```text
core/security/
├── authentication/            # 身份认证
├── authorization/             # 权限判断
├── credentials/               # Credential / Secret 抽象
├── tenant/                    # 多租户隔离（需要时）
└── context.py                 # 当前安全主体上下文
```

安全职责至少包括：

```text
Authentication
Authorization
Credential Management
Secret Management
Tenant Isolation（需要时）
Input Validation
Sensitive Data Protection
Security Audit
```

原则：

```text
Authentication = 你是谁
Authorization  = 你能做什么
Isolation      = 你能访问哪些资源
```

业务 Service 不应直接耦合 JWT、OAuth SDK、HTTP Header、Session Store 等具体实现；具体实现应通过 Security Contract 或 Adapter 隔离。

---

## 3.5 Core / Exceptions

推荐：

```text
core/exceptions/
├── base.py                    # 应用异常基类
├── codes.py                   # 稳定错误码
├── categories.py              # 错误分类
├── handlers.py                # FastAPI / 全局异常处理
└── responses.py               # 对外错误响应映射
```

错误分类建议：

```text
Validation
Authentication
Authorization
Domain
Application
Conflict
NotFound
Infrastructure
Timeout
Internal
```

要求：

- 错误码稳定；
- 错误分类明确；
- API 输出统一；
- 内部异常与外部错误分离；
- 保留诊断上下文；
- 禁止向客户端泄露密码、Token、Secret、内部堆栈和敏感数据。

Domain 专属异常仍应优先定义在所属 Service / Domain 内；只有需要统一处理、统一映射的异常才进入 Core。

禁止：

```python
try:
    ...
except Exception:
    pass
```

或用一个 `BusinessException` 吞并所有业务错误。

---

## 3.6 Core / Logging & Observability

推荐最小结构：

```text
core/
├── logging/
└── observability/
    ├── metrics/
    ├── tracing/
    ├── audit/
    └── correlation/
```

规模较小时也可以只保留：

```text
core/logging/
```

随着 Metrics、Tracing、Audit 增长再引入 `observability/`，不要求一次性创建空目录。

日志必须结构化，并尽可能关联：

```text
timestamp
level
service
operation
request_id
trace_id
correlation_id
execution_id（需要时）
tenant_id（按安全策略）
```

禁止记录：

```text
Password
Access Token
Refresh Token
完整 Secret
私钥
不必要的 PII
```

日志、Metrics、Tracing 应共享一致的 Correlation Context，避免出现“日志有 request_id、Trace 没有、Worker 又换一套 ID”的情况。

---

## 3.7 Core / Lifecycle

推荐：

```text
core/lifecycle/
├── startup.py
├── shutdown.py
├── health.py
└── readiness.py
```

负责：

```text
Startup
Shutdown
Graceful Shutdown
Health Check
Readiness Check
Resource Initialization
Resource Cleanup
```

不要把业务初始化流程、数据迁移业务逻辑或长期任务执行逻辑塞进 `startup.py`。

---

## 3.8 Core / Context

推荐：

```text
core/context/
├── request.py
├── tenant.py
├── execution.py
└── correlation.py
```

Context 只承载当前运行上下文，例如：

```text
request_id
trace_id
correlation_id
tenant_id
user_id
execution_id
```

禁止将持久化业务状态、缓存对象、大型数据集或数据库 Session 作为全局 Context 保存。

---

## 3.9 Common：跨模块共享定义

`common/` 用于保存**多个模块真正共享、稳定、低业务耦合的定义**。

推荐：

```text
common/
├── types/                     # 通用类型
├── enums/                     # 跨模块稳定枚举
├── constants/                # 稳定共享常量
└── protocols/                # Protocol / Port / Contract
```

### types

适合：

```text
ID 类型
分页类型
时间范围
通用 Result
通用排序 / 过滤类型
```

### enums

只有多个模块共同理解的枚举才能进入 Common。

例如：

```text
Environment
SortDirection
ProtocolVersion
```

具体业务状态应留在所属业务模块：

```text
services/<domain>/...
```

而不是把所有枚举集中到 `common/enums/`。

### constants

适合稳定的技术/协议常量，例如：

```text
协议版本
默认分页上限
通用 Header 名称
通用媒体类型
```

禁止把可配置业务规则、业务状态、业务阈值长期硬编码在 `common/constants/`。

### protocols

适合跨模块稳定抽象，例如：

```text
Clock
IDGenerator
UnitOfWork
EventPublisher
```

如果 Protocol 只服务一个 Domain，则应放在该 Domain / Service 内，而不是 Common。

---

## 3.10 Utils：纯技术辅助能力

`utils/` 是三个目录中约束最严格的目录。

定义：

> **无状态 + 低副作用 + 纯技术 + 无业务语义 + 可独立测试。**

推荐：

```text
utils/
├── datetime.py
├── json.py
├── hashing.py
├── text.py
└── encoding.py
```

典型函数：

```python
normalize_datetime(value)
safe_json_dumps(value)
sha256_digest(value)
normalize_text(value)
base64_encode(value)
```

禁止：

```text
utils/user.py
utils/order.py
utils/agent.py
utils/workflow.py
utils/database.py
utils/redis.py
utils/permission.py
utils/service.py
```

如果函数：

```text
访问数据库
访问 Redis
访问网络
调用 Provider
修改业务状态
执行权限决策
包含业务规则
```

则不应继续放在 Utils。

---

## 3.11 Core / Common / Utils 快速判断

```text
整个应用运行都依赖？             → core
跨多个模块稳定共享的定义？       → common
纯技术、无业务语义、无状态？     → utils
HTTP 接入？                       → api
FastAPI 依赖注入？               → dependencies
HTTP 横向处理？                  → middleware
ORM / Persistence Model？        → models
API DTO？                        → schemas
业务服务 / 用例？                → services
执行编排 / 状态运行时？          → runtime
调度触发？                       → scheduler
异步任务执行？                   → worker
Event / Command / 消费发布？     → messaging
数据库 / Redis / Provider 等实现？ → infrastructure
```

---

## 4. 现有目录的职责边界

### 4.1 api

只负责 HTTP 接入：

```text
路由
参数接收
认证依赖挂载
Schema 校验
调用 Service
响应转换
```

禁止在 Router 中实现复杂业务流程、数据库事务和 Provider 调用。

### 4.2 dependencies

负责 FastAPI DI：

```text
DB Session
Current User
Security Context
Request Context
Service Factory
```

Dependency 不应成为业务 Service 的替代品。

### 4.3 middleware

负责 HTTP 横向处理：

```text
Request ID
Correlation
CORS
Security Headers
Request Logging
Exception Boundary
Rate Limit（需要时）
```

禁止在 Middleware 中执行 Domain Business Logic。

### 4.4 models

负责 ORM / Persistence Model。

原则：

```text
Model ≠ API Schema
Model ≠ Domain Policy
Model ≠ Service
```

### 4.5 schemas

负责 HTTP DTO / API Contract。

禁止让 ORM Model 直接承担长期稳定的公开 API Contract。

随着项目规模扩大，可以进一步按 Domain 组织：

```text
schemas/
└── <domain>/
    ├── request.py
    └── response.py
```

### 4.6 services

`services/` 是业务用例和 Domain Service 的主要承载位置。

推荐：

```text
services/
└── <domain>/
    ├── service.py
    ├── policies.py
    └── validators.py
```

Service 可以编排：

```text
Domain Rule
Repository / Infrastructure Port
Transaction
External Adapter
Event
```

但不应把所有代码集中到单一 God Service。

### 4.7 runtime

只在存在复杂执行流程时启用。

负责：

```text
Execution
State Transition
Checkpoint
Resume
Recovery
```

不要把普通 CRUD Service 迁移到 Runtime。

### 4.8 scheduler

只负责：

```text
Trigger
Due Detection
Scheduling Policy
Job Creation
Dispatch
```

Scheduler 不负责长耗时业务执行。

### 4.9 worker

负责：

```text
Consume / Claim
Ownership
Execute
Retry
Timeout
ACK
Recovery
```

Worker 不应重新实现业务规则；业务执行应调用 Service / Runtime。

### 4.10 messaging

负责消息 Contract 和消息生命周期：

```text
Event
Command
Consumer
Publisher
Envelope
Serialization
```

Broker 的具体实现放在 `infrastructure/`。

### 4.11 infrastructure

负责外部技术实现：

```text
Database
Redis
Object Storage
Message Broker
HTTP Client
Third-party SDK
AI / Provider
```

业务代码依赖抽象；Infrastructure 实现抽象。

---

## 5. 分层与依赖

推荐依赖方向：

```text
API / Dependencies / Consumer
            ↓
         Services
            ↓
      Domain / Models
            ↓
   Infrastructure Adapters
```

横向能力：

```text
Core
Common
Utils
```

被需要的模块依赖，但不得反向吸收业务实现。

禁止：

```text
Core ─→ Service Business Logic
Common ─→ Domain Implementation
Utils ─→ Database Session
Domain/Service ─→ FastAPI Router
Domain/Service ─→ Vendor SDK
```

如果业务需要外部能力，应通过 Protocol / Port / Adapter 隔离。

---

## 6. Configuration

配置必须集中、类型化、可校验，并区分普通配置和 Secret。

推荐入口：

```text
core/config/
```

禁止：

```text
Router 直接读取环境变量
Service 直接读取 .env
Repository 自己解析配置
Worker 自己读取 Secret 文件
```

---

## 7. Security

安全能力统一遵循：

```text
Authentication
      ↓
Security Context
      ↓
Authorization
      ↓
Resource / Tenant Isolation
```

敏感信息必须：

```text
最小权限
最小暴露
安全存储
安全传输
安全日志
```

---

## 8. Error Handling

统一错误模型应覆盖：

```text
Validation
Authentication
Authorization
Domain
Application
Conflict
NotFound
Infrastructure
Timeout
Internal
```

HTTP、Worker、Messaging 可以有不同外部表现，但内部 Error Contract 应尽量保持一致。

---

## 9. Logging & Observability

关键请求、任务、消息和外部调用必须能够关联。

推荐统一上下文：

```text
request_id
trace_id
correlation_id
execution_id
```

Worker 和 Messaging 场景必须考虑跨进程传播，而不是重新生成无法关联的 ID。

---

## 10. API & Contract

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

破坏性变更必须有版本、兼容层或迁移方案。

---

## 11. Data & Transaction

- Repository / Infrastructure Adapter 负责数据访问。
- Service 负责用例级事务边界。
- Migration 必须版本化。
- 索引必须根据真实查询设计。
- ORM Model 不等于 Domain Policy。
- 跨服务一致性不得依赖共享数据库事务。

---

## 12. Concurrency & Idempotency

以下情况必须定义并发和幂等策略：

```text
Concurrent Request
Retry
Duplicate Message
Worker Crash
Timeout + Unknown Result
```

优先使用：

```text
Unique Constraint
Atomic Update
Version
Lease
Idempotency Key
```

不要把 Python 进程内锁当作分布式一致性机制。

---

## 13. Async / Background Processing

后台任务是可选能力。

简单短任务可以使用框架提供的后台任务；可靠、可重试、跨进程、长耗时任务应采用持久化 Job + Queue/Broker + Worker。

职责：

```text
Scheduler = Decide When
Queue     = Transport Work
Worker    = Execute Work
Runtime   = Execute Steps（需要时）
Recovery  = Repair Interrupted Work
```

---

## 14. Scheduler 通用架构

Scheduler 负责发现到期工作、创建 Job / Command 并可靠投递。

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

多实例必须具备重复调度保护；时间相关设计必须明确 UTC、Timezone、DST、Misfire 和 Clock Skew。

Scheduler 禁止执行长耗时业务。

---

## 15. Worker 通用架构

```text
Consume / Claim
      ↓
Ownership
      ↓
Lease / Fencing（需要时）
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

只有业务事实可靠提交后才 ACK。

---

## 16. Messaging / Outbox / Inbox

消息 Contract 与 Broker 实现分离：

```text
messaging/
    Event / Command / Consumer / Publisher

infrastructure/
    Broker Adapter
```

需要保证 DB 状态与消息发布一致时使用 Outbox；需要防止重复消费时使用 Inbox / Idempotency Record 等机制。

---

## 17. Runtime / Recovery / Checkpoint

复杂、长时间或可恢复执行流程应评估：

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

不要让 Runtime 与普通 Service 混合，避免执行状态和普通业务状态失去边界。

---

## 18. Microservice Architecture

微服务是可选架构，不是默认要求。

推荐演进：

```text
Modular Monolith
      ↓
明确业务边界 / 数据所有权 / 独立部署或扩缩容需求
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

禁止按 Controller、ORM Table 或文件类型机械拆服务。

---

## 19. External Integration

第三方 SDK、支付、邮件、存储、HTTP API、AI Provider 等通过 Adapter / Gateway 隔离。

业务代码依赖：

```text
Provider Contract
```

而不是直接依赖：

```text
Vendor SDK
```

外部调用必须定义 Timeout、Retry、错误映射、限流和日志脱敏。

---

## 20. Testing

最低要求按项目风险选择：

```text
Unit
Integration
API Contract
Database
Messaging（使用时）
End-to-End（关键流程）
```

Scheduler / Worker 项目还应测试：

```text
Duplicate Delivery
Concurrent Claim
Lease Expiration
Retry
DLQ
Crash Recovery
Idempotency
```

测试代码不得依赖不可控的真实外部服务，除非测试明确属于 `api_real/` 或其他真实集成测试范围。

---

## 21. Performance

性能优化必须基于测量：

```text
Profile
Measure
Optimize
Verify
```

重点关注：

```text
Database Query
Connection Pool
Network IO
Serialization
Concurrency
Queue Throughput
Memory
```

禁止未经测量通过增加缓存、线程、协程或微服务数量解决性能问题。

---

## 22. Deployment & Runtime

服务必须支持：

```text
Graceful Startup
Readiness
Health Check
Graceful Shutdown
Configuration Validation
```

Scheduler、Worker、API 可以是不同运行角色，但应尽量复用同一应用基础能力和配置体系。

---

## 23. Definition of Done

后端功能完成至少需要确认：

```text
[ ] 目录职责正确
[ ] Core/Common/Utils 边界正确
[ ] API Contract 明确
[ ] Error Contract 明确
[ ] Security 已考虑
[ ] Transaction Boundary 明确
[ ] Idempotency 已评估
[ ] Logging / Trace 可关联
[ ] 外部依赖已隔离
[ ] Unit Test 通过
[ ] 必要 Integration / Contract Test 通过
[ ] Migration 已同步（涉及 DB 时）
[ ] Documentation 已更新
```

最终原则：

> **不以目录数量衡量架构质量，而以职责唯一、依赖单向、边界稳定、基础设施可替换、代码可测试和系统可演进衡量架构质量。**
