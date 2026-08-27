# 后端新功能模块与新业务功能扩展准则

> **定位**：本文是 `FastAPI + Python` 后端在既有目录架构基础上的功能扩展规范。它不重构既有目录，不新增另一套架构；重点规定当项目新增业务功能、横向能力、异步任务、消息能力或外部集成时，应如何在现有结构内进行增量扩展。

## 1. 适用范围

适用于：

- 新增业务 Domain / 子功能；
- 现有业务新增 API、Service、数据模型；
- 新增第三方系统集成；
- 新增消息、异步任务、定时任务；
- 新增 Runtime 执行能力；
- 新增公共基础能力；
- 新增数据库表、索引和 Migration。

核心原则：

> **新增功能应当“向现有架构填充模块”，而不是“每新增一个需求就重新创建一套架构”。**

---

## 2. 新功能扩展总流程

```text
需求
 ↓
业务边界识别
 ↓
模块归属判断
 ↓
Contract / 数据模型设计
 ↓
API / Service / Model / Infrastructure 实现
 ↓
Error / Security / Observability
 ↓
Transaction / Idempotency / Concurrency
 ↓
Unit Test / Integration / Contract Test
 ↓
Migration / Configuration
 ↓
Documentation
 ↓
Review / CI
 ↓
Done
```

不得跳过业务边界和模块归属判断直接创建代码文件。

---

## 3. 首先判断“新增的是什么”

新需求至少归入以下一种能力：

```text
业务功能
横向核心能力
公共共享定义
纯技术工具
外部基础设施
API Contract
消息能力
异步执行
调度能力
运行时能力
```

推荐判断：

| 类型 | 目录 |
|---|---|
| HTTP 接入 | `app/api/v1/<domain>/` |
| FastAPI DI | `app/dependencies/` |
| HTTP 横向能力 | `app/middleware/` |
| ORM / Persistence Model | `app/models/` |
| HTTP DTO / API Schema | `app/schemas/` |
| 业务 Service | `app/services/<domain>/` |
| 执行编排 | `app/runtime/` |
| 调度 | `app/scheduler/` |
| Worker | `app/worker/` |
| Event / Command / Consumer / Publisher | `app/messaging/` |
| 外部技术实现 | `app/infrastructure/` |
| 应用级核心能力 | `app/core/` |
| 跨模块稳定定义 | `app/common/` |
| 纯技术工具 | `app/utils/` |

`runtime/`、`scheduler/`、`worker/`、`messaging/` 属于按需启用的能力，并非所有项目或所有功能都必须创建。

---

## 4. 新业务功能扩展规则

### 4.1 先确定业务边界

新增业务功能必须先回答：

```text
业务对象是什么？
业务规则是什么？
业务状态是什么？
谁可以操作？
数据归谁所有？
生命周期是什么？
是否产生事件？
是否需要异步执行？
是否需要独立事务？
```

如果只是现有 Domain 的新增能力，应优先扩展现有 Domain，而不是创建新的顶级业务目录。

### 4.2 标准扩展方式

沿用既有架构：

```text
app/
├── api/v1/<domain>/
├── schemas/<domain>/
├── services/<domain>/
└── models/<domain>/
```

例如新增订单能力：

```text
api/v1/orders/
schemas/orders/
services/orders/
models/orders/
```

禁止因为一个新需求创建：

```text
app/order_create/
app/order_update/
app/order_query/
```

---

## 5. API 扩展规则

Router 只负责 HTTP 接入：

```text
路由
参数接收
认证 / 授权依赖
Schema 校验
调用 Service
响应转换
```

标准调用链：

```text
HTTP Request
    ↓
Router
    ↓
Schema Validation
    ↓
Service
    ↓
Repository / Infrastructure
    ↓
Response Schema
```

禁止：

```text
Router → 直接 SQL
Router → 直接 Redis
Router → 直接 Provider SDK
Router → 复杂业务流程
```

破坏性 API 变更必须提供版本、兼容层或迁移方案。

---

## 6. Schema 扩展规则

Request 与 Response 应按用途拆分：

```text
Create
Update
Query
List
Detail
Response
```

例如：

```text
CreateOrderRequest
UpdateOrderRequest
OrderQuery
OrderListResponse
OrderDetailResponse
```

禁止直接将 ORM Model 作为公开 API Contract：

```text
ORM Model ≠ API Schema
```

Schema 应保持与数据库内部实现解耦。

---

## 7. Service 扩展规则

Service 负责业务用例和业务编排：

```text
业务规则协调
事务边界
Repository / Infrastructure Port 调用
权限协调
状态变化
Event 发布
```

Service 不负责：

```text
HTTP Request / Response
ORM 初始化
Provider SDK 细节
JWT 解析
日志基础设施实现
```

禁止不断向单个 Service 添加功能形成 God Service。出现明显职责增长时，应按业务能力拆分 Service 内部模块。

---

## 8. Model / Database 扩展规则

新增持久化功能必须同时评估：

```text
ORM Model
Migration
Primary Key
Foreign Key
Unique Constraint
Index
Nullable
Default
Lifecycle
Transaction
```

标准流程：

```text
数据模型设计
 ↓
ORM Model
 ↓
Migration
 ↓
Constraint / Index
 ↓
Repository
 ↓
Service
 ↓
API
```

禁止只修改 ORM Model 而不提供 Migration。

索引必须根据真实查询场景设计，禁止无依据地为所有字段添加索引。

---

## 9. Infrastructure 扩展规则

新增以下能力时，应进入 Infrastructure：

```text
Database
Redis
Object Storage
Message Broker
HTTP Client
Search Engine
Email
Payment Provider
AI Provider
第三方 SDK
```

推荐：

```text
Business Service
      ↓
Contract / Protocol / Port
      ↓
Infrastructure Adapter
      ↓
Vendor SDK / External API
```

业务代码不得直接绑定第三方 SDK 的具体类型、异常和生命周期。

外部调用必须评估：

```text
Timeout
Retry
Rate Limit
Circuit Breaker（需要时）
Error Mapping
Idempotency
Logging / Redaction
```

---

## 10. Core / Common / Utils 扩展规则

### Core

只有整个应用运行所需的横向核心能力才进入 `core/`：

```text
config
security
exceptions
logging
observability
lifecycle
context
```

禁止：

```text
core/order/
core/user/
core/payment/
core/business/
```

### Common

只有满足：

```text
跨多个模块
稳定
低业务耦合
共享语义明确
```

才进入 `common/`。

业务状态、业务实体和单一 Domain 的 Protocol 不应为了“复用”提前提升到 Common。

### Utils

必须尽量满足：

```text
无状态
纯技术
无业务语义
低副作用
可独立测试
```

一旦涉及数据库、网络、Provider、权限决策或业务规则，就应移出 Utils。

---

## 11. Messaging 扩展规则

新增异步消息能力时先区分：

```text
Command = 请求执行一个动作
Event   = 一个事实已经发生
```

例如：

```text
CreateOrderCommand
OrderCreatedEvent
```

消息 Contract 位于：

```text
app/messaging/
```

Broker 的具体实现位于：

```text
app/infrastructure/
```

禁止使用一个万能 `Message` 类型承载所有业务语义。

需要保证数据库状态与消息发布一致时，应评估 Outbox；需要防止重复消费时，应评估 Inbox / Idempotency Record。

---

## 12. Scheduler 扩展规则

只有存在以下需求时才增加 Scheduler 能力：

```text
定时任务
周期任务
延迟任务
到期触发
重试触发
```

职责边界：

```text
Scheduler = Decide When
Queue     = Transport Work
Worker    = Execute Work
Service   = Business Logic
```

Scheduler 负责发现到期工作、创建任务和可靠投递，不负责长耗时业务执行。

多实例部署必须考虑：

```text
Duplicate Trigger
Atomic Claim
Lease
Misfire
Timezone
DST
Clock Skew
```

---

## 13. Worker 扩展规则

新增 Worker 时，业务逻辑仍应复用 Service / Runtime：

```text
Consumer
 ↓
Claim / Ownership
 ↓
Idempotency
 ↓
Service / Runtime
 ↓
Commit
 ↓
ACK
```

Worker 必须评估：

```text
Retry
Timeout
Backpressure
Graceful Shutdown
Dead Letter
Poison Message
Crash Recovery
Duplicate Delivery
```

只有业务事实可靠提交后才 ACK。

---

## 14. Runtime 扩展规则

只有复杂、长时间、可暂停、可恢复或多步骤执行流程才进入：

```text
app/runtime/
```

典型流程：

```text
Step
 ↓
State
 ↓
Checkpoint
 ↓
Crash
 ↓
Recovery
 ↓
Resume / Retry / Compensate
```

普通 CRUD 不应为了“统一”而进入 Runtime。

---

## 15. 幂等与并发扩展规则

新增功能必须明确是否存在：

```text
重复请求
重复消息
重试
超时但结果未知
并发更新
Worker Crash
```

根据风险选择：

```text
Unique Constraint
Optimistic Version
Atomic Update
Idempotency Key
Deduplication Record
Lease / Fencing
```

不得依赖 Python 进程内锁解决跨进程一致性问题。

---

## 16. Security 扩展规则

新增接口和业务功能必须重新评估：

```text
Authentication
Authorization
Resource Ownership
Tenant Isolation
Input Validation
Sensitive Data
Audit
Rate Limit
```

新增敏感字段时必须同步考虑：

```text
Storage Encryption（需要时）
Transport Encryption
Access Control
Logging Redaction
Retention
Deletion
```

不能因为功能属于“内部接口”而默认跳过权限设计。

---

## 17. Error 扩展规则

新增功能应优先使用已有统一错误体系。

只有确实具有新业务语义时才增加新的 Error Code / Category。

错误必须区分：

```text
Expected Business Error
Validation Error
Authorization Error
Infrastructure Failure
Unexpected Internal Error
```

禁止通过增加大量异常类型掩盖不清晰的业务边界。

---

## 18. Observability 扩展规则

新 API、任务、消息和外部调用应具备可关联性：

```text
request_id
trace_id
correlation_id
execution_id（需要时）
```

关键业务操作需要审计时，应进入 Audit，而不是单纯依赖普通 Debug Log。

日志必须脱敏，禁止输出：

```text
Password
Token
Secret
Private Key
不必要的 PII
```

---

## 19. Configuration 扩展规则

新增功能涉及配置时：

```text
新增 Typed Setting
 ↓
默认值 / 必填性
 ↓
环境覆盖
 ↓
启动校验
 ↓
Documentation
```

禁止：

```text
Service 直接 os.getenv()
Router 直接读取 .env
Worker 自己读取 Secret 文件
```

Secret 不得写入 Git、配置文件模板中的真实值或日志。

---

## 20. 测试扩展规则

根据功能风险选择测试类型：

```text
Unit
Integration
API Contract
Messaging
API Real
```

普通业务至少覆盖：

```text
业务规则
正常路径
关键异常路径
边界条件
```

异步功能还必须评估：

```text
Duplicate Delivery
Concurrent Claim
Retry
Timeout
DLQ
Crash Recovery
Idempotency
```

---

## 21. 文档同步规则

新增功能至少同步检查：

```text
API
Architecture
Configuration
Database
Messaging
Deployment
Testing
```

涉及外部 Contract 时必须记录版本、兼容策略和迁移方式。

代码完成但文档未更新，不应视为完整交付。

---

## 22. 防止目录和模块无序膨胀

新增代码优先扩展现有业务模块：

```text
services/orders/
├── service.py
├── commands.py
├── queries.py
└── policies.py
```

只有在出现明确独立边界时才拆出新的模块。

判断标准：

```text
独立业务概念
独立生命周期
独立权限边界
独立数据所有权
独立扩展方向
独立测试边界
```

不要因为一个文件超过一定行数就机械拆分目录；应根据职责而不是文件大小拆分。

---

## 23. 新功能 Definition of Done

```text
[ ] 已明确业务 / 技术边界
[ ] 已确认现有目录归属
[ ] 未重复创建已有基础能力
[ ] API Contract 已定义
[ ] Schema 已定义
[ ] Service 职责明确
[ ] Model / Migration 已同步（涉及 DB 时）
[ ] Infrastructure 已隔离（涉及外部系统时）
[ ] Error Handling 已设计
[ ] Security 已评估
[ ] Transaction Boundary 已明确
[ ] Idempotency / Concurrency 已评估
[ ] Logging / Trace / Audit 已评估
[ ] Async / Scheduler / Worker 已按需设计
[ ] Unit Test 已通过
[ ] 必要 Integration / Contract Test 已通过
[ ] Configuration 已同步
[ ] Documentation 已同步
[ ] Code Review / CI 已通过
```

---

## 24. 禁止的扩展模式

### 24.1 为一个功能创建完整新架构

```text
❌ new_feature/
   ├── controller/
   ├── service/
   ├── repository/
   ├── model/
   └── utils/
```

如果项目已有统一目录，应遵循已有目录结构。

### 24.2 把业务代码放进 Core

```text
❌ core/order_service.py
```

### 24.3 把业务对象放进 Common

```text
❌ common/order.py
```

除非它是真正跨业务边界的稳定公共 Contract。

### 24.4 把基础设施放进 Utils

```text
❌ utils/redis.py
❌ utils/database.py
❌ utils/http_client.py
```

### 24.5 Router 直接实现业务

```text
❌ Router
   ├── SQL
   ├── Redis
   ├── Provider
   └── Business Rules
```

### 24.6 Worker 重新实现 Service

```text
❌ HTTP 有一套业务逻辑
❌ Worker 再复制一套业务逻辑
```

应该复用同一业务 Service / Runtime。

---

## 25. 架构演进原则

功能增加不意味着目录必须增加。

优先顺序：

```text
扩展现有模块
      ↓
模块内部职责拆分
      ↓
明确业务边界
      ↓
形成独立模块
      ↓
必要时 Service Extraction
      ↓
必要时 Microservice
```

不要直接：

```text
新需求
 ↓
新 Service
 ↓
新微服务
```

微服务拆分必须有明确的数据所有权、部署独立性、团队边界、扩缩容或故障隔离收益。

---

## 26. 最终扩展原则

> **任何新增功能都必须首先适配现有架构，而不是让现有架构迁就单个功能。**

判断一个扩展是否健康，应重点检查：

```text
职责是否唯一？
模块边界是否清晰？
依赖方向是否正确？
是否复用了已有能力？
是否产生重复实现？
是否引入了不必要的基础设施？
是否具备安全边界？
是否具备错误处理？
是否可观测？
是否可测试？
是否可回滚？
未来是否可以独立演进？
```

最终目标不是让目录越来越复杂，而是让**业务增长、代码增长和架构复杂度保持可控增长**。
