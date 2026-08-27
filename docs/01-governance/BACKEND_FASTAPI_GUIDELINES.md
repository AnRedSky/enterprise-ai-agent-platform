# FastAPI + Python 后端通用项目开发准则

> **定位**：本文件定义基于 FastAPI + Python 的企业级后端项目通用工程规范。它是可复制到其他 FastAPI 项目的技术开发基线，不记录具体项目阶段进度。
>
> 本文件遵循 `UNIVERSAL_DEVELOPMENT_GUIDELINES.md`。项目自身的 `DEVELOPMENT.md` 可以补充 Python 版本、包管理器、数据库、缓存、部署和测试命令，但不得无故违反核心工程原则。

---

## 1. 核心原则

1. **Contract First**：先定义 API / Domain Contract，再实现业务。
2. **Domain First**：业务规则属于 Domain / Service，不属于 Router、ORM Model 或 Middleware。
3. **Dependency Direction**：业务依赖稳定抽象，Infrastructure 负责技术适配。
4. **Transaction Explicit**：事务边界必须明确，禁止隐式跨层事务。
5. **State as Fact**：数据库持久化状态是业务事实，缓存和消息系统不能无约束地成为第二事实源。
6. **Idempotency First**：所有可能重试、并发调用、异步消费的操作都必须定义幂等语义。
7. **Failure First**：Timeout、Retry、Conflict、Recovery、Partial Failure 都是正式设计的一部分。
8. **Security by Boundary**：Authentication、Authorization、Tenant Isolation、Secret 管理必须形成明确边界。
9. **Observable by Default**：关键请求、任务、恢复和外部调用必须具备可关联的日志、Trace 和 Metrics。
10. **No Duplicate Capability**：同一能力只保留一个正式实现入口。

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
uv / Poetry / pip-tools 等受控包管理方式
```

项目可以替换具体组件，但必须保持等价的 API、Validation、ORM、Migration、Test 和 Observability 能力。

## 3. 推荐目录结构

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/<domain>/       # HTTP Router
│   ├── core/                  # 配置、安全、异常、日志等核心能力
│   ├── dependencies/          # FastAPI DI / Request Context
│   ├── middleware/            # HTTP 横向处理
│   ├── models/                # ORM Model
│   ├── schemas/               # HTTP DTO / API Schema
│   ├── services/              # Domain Service
│   │   └── <domain>/
│   ├── runtime/               # 执行编排
│   ├── infrastructure/        # DB / Redis / Provider / HTTP
│   ├── utils/                 # 无业务语义纯工具
│   └── main.py
├── migrations/
├── scripts/
└── tests/
    ├── unit/
    ├── integration/
    ├── api_contract/
    └── api_real/
```

## 4. 分层职责

```text
Router
 ↓
Dependency / Context
 ↓
Service / Domain
 ↓
Runtime（存在执行编排时）
 ↓
Repository / Gateway
 ↓
ORM / Infrastructure
```

### API

负责：

```text
HTTP Method
Path
Request Parsing
Response Serialization
Status Code
Authentication entry
```

禁止在 Router 中堆积核心业务规则或直接执行复杂 ORM 操作。

### Dependency

负责：

```text
Current User
Tenant Context
DB Session
Permission Context
Request Context
```

禁止把业务流程藏入 Dependency。

### Service / Domain

负责：

```text
Business Rule
Policy
State Transition
Domain Validation
Repository orchestration
```

### Repository

负责持久化访问与查询抽象。

Repository 不应决定业务政策。

### Infrastructure

负责：

```text
PostgreSQL
Redis
HTTP Client
Model Provider
Object Storage
Message Broker
```

Infrastructure 不得反向承载业务规则。

## 5. Domain Module

推荐：

```text
services/<domain>/
├── __init__.py
├── contract.py
├── service.py
├── repository.py
├── policy.py
└── ...
```

只有存在真实职责时才创建文件。

禁止为了“标准结构”强制创建：

```text
manager.py
handler.py
facade.py
helper.py
```

## 6. API Contract

推荐：

```text
OpenAPI
 ↓
Pydantic Schema
 ↓
Domain Contract
 ↓
Service
```

ORM Model 不得直接作为公开 API Contract。

Request / Response Schema 应明确：

```text
Required / Optional
Enum
Format
Validation
Nullable
Error Contract
Pagination
```

破坏性 API 变更必须显式版本化或执行兼容迁移。

## 7. Pydantic Schema

Schema 负责数据边界验证，不负责复杂业务流程。

推荐：

```text
Input DTO
Output DTO
Internal Domain DTO（需要时）
```

禁止直接把巨大 ORM Object 通过 `from_attributes` 无约束暴露成 API。

敏感字段必须明确控制序列化范围。

## 8. FastAPI Router

Router 应保持薄：

```python
@router.post(...)
async def create(...):
    command = ...
    result = service.create(command)
    return response_schema(result)
```

Router 不应包含：

```text
复杂 SQL
多层业务 if/else
Retry Loop
Recovery Policy
Provider SDK 直接调用
```

## 9. Dependency Injection

使用 FastAPI Dependency Injection 管理：

```text
DB Session
Current User
Tenant Context
Authorization Context
Service Factory
```

避免 Service 自己创建数据库 Session、HTTP Client 或全局状态。

## 10. 数据库规范

数据库负责持久化业务事实。

所有 Schema 变更必须通过 Migration 管理：

```text
Model Change
 ↓
Migration
 ↓
Migration Test
 ↓
Deploy
```

禁止依赖启动时自动 `create_all()` 替代生产 Migration。

## 11. Transaction Boundary

事务必须对应明确业务操作：

```text
Service Command
 ↓
Transaction
 ├── Validate
 ├── Write
 └── Commit
```

禁止：

```text
Router 开事务
Repository 私自 commit
Service 再开第二事务
```

事务边界必须可解释。

对于跨外部系统操作，不允许假设数据库 Transaction 可以覆盖 HTTP Provider、消息队列等外部副作用。

## 12. Repository 规则

Repository 只做：

```text
Query
Insert
Update
Delete
Lock
Persistence Mapping
```

业务 Policy 不进入 Repository。

高并发更新必须明确：

```text
Optimistic Lock
Pessimistic Lock
Atomic UPDATE
Unique Constraint
Idempotency Key
```

不能仅依赖 Python 层 if 判断解决数据库竞争。

## 13. 并发与幂等

所有以下场景必须主动设计：

```text
重复 HTTP Request
Retry
Double Click
Message Redelivery
Scheduler overlap
Multi Worker
Timeout after commit
Client reconnect
```

幂等键应具有明确作用域：

```text
tenant + operation + resource + idempotency_key
```

具体组成按业务定义。

## 14. 状态机

涉及状态流转的 Domain 必须定义：

```text
State
Event
Legal Transition
Illegal Transition
Terminal State
Recovery State
```

禁止多个 Service 各自修改同一个状态字段而没有统一 Contract。

推荐通过显式 transition API / Domain Service 控制状态推进。

## 15. Scheduler / Worker / Async Runtime

异步执行系统必须明确：

```text
Scheduler
 = 什么时候检查 / 触发

Queue
 = 如何传递工作

Worker
 = 谁执行

Runtime
 = 如何执行步骤

Persistence
 = 事实如何记录
```

不要让 Scheduler 同时承担业务执行。

Worker 必须考虑：

```text
Claim
Lease
Heartbeat
Ownership
Fencing
Timeout
Retry
Recovery
```

Lease 丢失后旧 Worker 必须停止继续推进受保护的执行；不能等下一次数据库更新失败才视为完成。

## 16. AI Provider / External Gateway

所有外部 Provider 必须集中在 Infrastructure：

```text
services/
    ↓
Provider Contract
    ↓
infrastructure/providers/
    ↓
External API / SDK
```

禁止业务 Service 直接散落第三方 SDK 调用。

Provider 必须统一处理：

```text
Timeout
Retry
Rate Limit
Error Mapping
Credential
Telemetry
```

同一 Provider 能力只保留一个正式适配实现。

## 17. AI Agent Runtime

Agent 执行必须明确分离：

```text
Agent Policy
 ↓
Model Provider
 ↓
Tool Selection
 ↓
Permission Check
 ↓
Tool Execution
 ↓
Observation
 ↓
Next Step
```

LLM 输出必须经过 Schema / Policy Validation 后才能触发敏感工具。

不要让 Prompt 本身成为权限系统。

## 18. Authentication / Authorization

认证与授权必须分开：

```text
Authentication
 = 你是谁

Authorization
 = 你能做什么
```

授权至少考虑：

```text
User
Role
Permission
Resource
Tenant
Operation
```

后端必须是最终安全边界。

## 19. Tenant Isolation

多租户系统必须明确租户上下文来源：

```text
Authenticated Principal
 ↓
Trusted Tenant Context
 ↓
Service
 ↓
Repository
```

禁止信任客户端任意提交的 `tenant_id` 作为授权依据。

关键查询必须确保 Tenant Scope，不得只依赖调用方“记得加过滤条件”。

## 20. Secret 管理

禁止：

```text
源码中的 Secret
Git 中的生产凭据
日志中的 Token
API Response 中回传 Secret
Prompt 中暴露 credential
```

Secret 应通过受控环境变量、Secret Manager 或等价安全设施注入。

## 21. Error Contract

建立稳定 Error Model，例如：

```text
error_code
message
details
request_id
trace_id
```

错误分类至少包括：

```text
Validation
Authentication
Authorization
Not Found
Conflict
Rate Limit
Provider
Timeout
Internal
```

不要向客户端泄漏 Python Traceback、SQL、Secret 或内部网络信息。

## 22. Exception Handling

推荐统一：

```text
Domain Exception
 ↓
Application Error Mapping
 ↓
HTTP Error Response
```

不要在每个 Router 重复 try/except。

异常捕获必须有处理目的；禁止：

```python
except Exception:
    pass
```

或无上下文地吞掉异常。

## 23. Timeout / Retry / Circuit Breaker

外部调用必须有明确 timeout。

Retry 必须满足：

```text
Retryable Error
+ Idempotent Operation
+ Bounded Attempts
+ Backoff
```

禁止对所有异常无脑 retry。

高风险 Provider 或关键基础设施可根据实际需求增加 Circuit Breaker / Bulkhead / Rate Limit。

## 24. Background Task

FastAPI BackgroundTasks 不能被默认当作可靠的 Durable Job Queue。

如果任务要求：

```text
可靠执行
跨进程
重试
持久化
恢复
```

必须使用正式 Job / Queue / Worker 架构。

## 25. Redis / Cache

Cache 不是默认事实源。

必须定义：

```text
Key
TTL
Invalidation
Consistency
Stampede protection
Failure behavior
```

Redis 故障时必须明确业务是：

```text
Fail Open
Fail Closed
Degrade
Reject
```

## 26. 外部 HTTP Client

HTTP Client 必须集中配置：

```text
Connect Timeout
Read Timeout
Total Timeout
Connection Pool
Retry
Headers
Trace Context
Error Mapping
```

不得在业务代码中散落 `httpx.AsyncClient()` 生命周期管理。

## 27. Logging

日志必须结构化并包含适当上下文：

```text
timestamp
level
service
operation
request_id
trace_id
tenant_id（按安全策略）
error_code
```

禁止记录：

```text
Password
Token
Secret
Provider Credential
完整敏感 Payload
```

## 28. Observability

关键链路推荐：

```text
Request
 ↓
Service
 ↓
DB / Redis / Provider
 ↓
Background Job
 ↓
Worker
```

通过 `request_id / trace_id` 建立关联。

异步链路必须显式传播 Trace Context，而不是依赖进程内变量。

## 29. Metrics

至少关注：

```text
Request latency
Request error rate
DB latency
Provider latency
Queue depth
Worker execution
Retry count
Recovery count
Lease loss
```

Metrics 标签必须控制 Cardinality，禁止直接把 user input、完整 URL、UUID 等无限维字段作为标签。

## 30. Testing

推荐四层：

```text
Unit
 ↓
Integration
 ↓
API Contract
 ↓
Real API / System
```

### Unit

测试：

```text
Domain Rule
Policy
State Transition
Pure Function
Retry Decision
Recovery Decision
```

### Integration

测试：

```text
Repository
Transaction
Database
Redis
Provider Adapter
```

### API Contract

测试：

```text
HTTP Method
Path
Request
Response
Status Code
Error Contract
Authorization
```

### Real API

仅在需要真实外部 Provider / DB / HTTP 时执行。

## 31. Test Isolation

测试实现与测试编排分离：

```text
tests/                  # assertions
scripts/test/           # gates / orchestration
scripts/evaluation/     # quality evaluation
scripts/dev/            # local development helpers
```

测试脚本不应偷偷改变生产数据或负责启动生产级服务，除非明确属于环境编排工具。

## 32. Migration Testing

涉及数据库 Migration 的任务至少验证：

```text
Migration syntax
Upgrade
Current head
Downgrade（项目需要时）
Model / schema consistency
```

多实例部署必须考虑 Migration 与应用版本兼容窗口。

## 33. Configuration

配置必须集中管理并分层：

```text
Default
Environment
Secret
Runtime override（明确允许时）
```

不要在业务代码中读取环境变量并自己解释。

推荐统一 Settings / Configuration Boundary。

## 34. Performance

优化顺序：

```text
Correctness
 ↓
Measure
 ↓
Identify bottleneck
 ↓
Optimize
 ↓
Benchmark
 ↓
Regression test
```

重点关注：

```text
N+1 Query
Connection Pool
Blocking IO
Async misuse
Large Payload
Serialization
External API latency
```

禁止没有指标支撑的“性能优化”。

## 35. Async / Sync 边界

Async Endpoint 中不得直接执行长时间阻塞操作。

必须识别：

```text
CPU-bound
IO-bound
Blocking SDK
Async SDK
```

CPU-intensive 工作应移交适当 Worker / Process / Job 系统。

## 36. Code Quality

推荐：

```text
ruff / lint
formatter
mypy / pyright（项目需要时）
pytest
```

函数应保持单一职责；复杂逻辑优先拆 Domain Policy，而不是无限增加条件分支。

## 37. Python 类型规范

推荐开启严格类型检查能力。

禁止通过：

```python
Any
# type: ignore
cast(Any, ...)
```

长期掩盖真实类型问题。

对第三方库类型缺失可以局部隔离并记录原因。

## 38. Docstring / Comment

新增模块顶部至少说明：

```text
模块职责
边界
关键外部依赖
```

复杂公共类 / 方法说明业务意图与约束。

禁止通过大量注释掩盖职责混乱。

## 39. Refactor

完整重构必须：

```text
建立目标模块
 ↓
迁移生产代码
 ↓
迁移测试
 ↓
删除旧实现
 ↓
全仓搜索旧 import
 ↓
重复实现检查
 ↓
测试
```

禁止长期保留兼容代理、旧入口、双 Service、双 Provider。

## 40. Git / Commit

推荐：

```text
feat(backend): ...
fix(backend): ...
refactor(backend): ...
test(backend): ...
chore(backend): ...
```

一个 Commit 尽量对应一个可解释工程变化。

## 41. 新 Feature 标准流程

```text
① 阅读项目 DEVELOPMENT.md
② 同步最新 main / 工作分支
③ 搜索已有 Domain / Service / Repository / Provider
④ 确认 API Contract
⑤ 定义 Domain Boundary
⑥ 定义 State / Error / Idempotency
⑦ 定义 Migration（需要时）
⑧ 实现 Repository
⑨ 实现 Service / Policy
⑩ 实现 Runtime（需要时）
⑪ 实现 API Schema
⑫ 实现 Router
⑬ Unit Test
⑭ Integration / API Contract Test
⑮ Real API（需要时）
⑯ 更新文档 / Status / Acceptance
⑰ Commit / Review
```

## 42. Definition of Done

```text
[ ] Domain boundary clear
[ ] API Contract defined
[ ] Authorization considered
[ ] Tenant isolation considered
[ ] State transition defined
[ ] Idempotency defined
[ ] Transaction boundary defined
[ ] Timeout / Retry defined
[ ] Error Contract defined
[ ] Migration completed（需要时）
[ ] Unit tests
[ ] Integration / Contract tests（适用时）
[ ] Observability added
[ ] No secret leakage
[ ] No duplicate implementation
[ ] Documentation updated
[ ] Git change traceable
```

## 43. 禁止事项

```text
❌ Router 承载核心业务逻辑
❌ ORM Model 直接作为公开 Contract
❌ Repository 决定业务 Policy
❌ Service 自己创建全局 DB Session
❌ 多套 Provider 实现同一能力
❌ 任意客户端 tenant_id 决定权限
❌ 非幂等操作无脑 Retry
❌ 无 Timeout 的外部 HTTP 调用
❌ BackgroundTasks 冒充 Durable Queue
❌ except Exception 后吞异常
❌ Cache 直接成为第二事实源
❌ Secret / Token 写入日志或代码
❌ 只测试成功路径
❌ 用兼容层掩盖重构未完成
❌ 未测量的性能优化
```

## 44. 与项目治理文档的关系

```text
UNIVERSAL_DEVELOPMENT_GUIDELINES.md
            ↓
FastAPI + Python 通用准则
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

本文件解决“FastAPI + Python 项目应该如何工程化”；具体项目负责补充数据库、缓存、队列、部署、CI/CD、命令和实际测试环境。
