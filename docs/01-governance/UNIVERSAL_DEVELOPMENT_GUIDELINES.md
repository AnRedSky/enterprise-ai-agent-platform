# 通用项目开发准则

> **定位**：本文件从企业级 AI Agent / 后端 / 前端 / 分布式执行项目的实际工程经验中抽象出一套与具体技术栈无关的通用开发准则，可复制到后续新项目作为工程治理基线。
>
> 本文件只定义**通用工程原则、开发流程、架构边界、测试、数据、安全、可观测性、版本控制、文档与交付规则**，不绑定具体语言、框架、数据库或云厂商。
>
> 项目落地时，应由项目自己的 `DEVELOPMENT.md`、架构文档或治理文档将本准则映射为具体技术栈、目录结构、命令和验收 Gate。

---

## 1. 核心原则

### 1.1 以工程交付为中心

开发任务必须以**可运行、可验证、可追踪、可维护**为完成标准，而不是以“代码已经写完”作为完成标准。

每个功能交付至少应形成：

```text
需求
 ↓
架构 / Contract
 ↓
实现
 ↓
测试
 ↓
验收
 ↓
文档 / 状态记录
 ↓
版本提交
```

### 1.2 先边界，后实现

任何新增功能先回答：

1. 属于哪个业务领域？
2. 输入与输出是什么？
3. 谁拥有业务规则？
4. 谁负责持久化？
5. 谁负责执行编排？
6. 谁负责外部技术适配？
7. 谁负责错误、重试、超时与恢复？
8. 谁负责可观测性？

禁止先创建一个“大 Service / Manager / Utils”再逐步把所有职责塞进去。

### 1.3 单一事实源

同一种业务事实、业务规则、状态转换或外部能力必须尽量只有一个正式实现入口。

```text
一个业务规则      → 一个正式计算 / 校验入口
一个外部能力      → 一个 Provider / Adapter 入口
一个状态机        → 一个状态转换权威入口
一个持久化事实    → 一个权威数据源
一个 API Contract  → 一个正式契约定义
```

测试可以验证生产算法，但不得复制一套生产算法作为“测试实现”。

### 1.4 不以兼容层掩盖架构问题

架构迁移必须明确迁移终点。除非有明确的产品兼容需求，否则禁止长期保留：

- 旧模块代理；
- 旧入口转发；
- 重复 Provider；
- 双 Service；
- 双 Repository；
- 双 Runtime；
- 为了迁移方便而永久存在的兼容垫片。

兼容逻辑必须记录：**兼容对象、保留原因、移除条件、截止时间和不可扩展边界**。

---

## 2. 开发前基线确认

每次开发开始前必须确认当前代码基线，而不是直接在旧工作区继续修改。

标准流程：

```text
同步远端基线
    ↓
确认当前版本 / Commit
    ↓
读取项目治理规则
    ↓
读取当前架构 / Phase / Status
    ↓
检查已有实现
    ↓
确认任务边界
    ↓
开始开发
```

### 强制检查

- 当前分支 / 工作区状态明确；
- 基线版本明确；
- 当前任务没有被其他提交覆盖或废弃；
- 已搜索现有 Domain、Service、Repository、Runtime、Provider、工具和测试；
- 已确认是否存在可复用的正式实现；
- 已确认相关 API / Event / Data Contract；
- 已确认相关数据库结构与 Migration 状态；
- 已确认当前阶段的测试范围和验收标准。

---

## 3. 需求与任务拆解

### 3.1 需求必须转化为可验证行为

禁止使用以下模糊完成条件：

```text
“基本完成”
“功能差不多了”
“接口可以用了”
“应该没有问题”
```

应转换为：

```text
Given → When → Then
```

或：

```text
输入
 → 处理
 → 状态变化
 → 持久化事实
 → 输出
 → 异常 / 边界行为
```

### 3.2 每个任务必须明确

- Scope：做什么；
- Non-scope：明确不做什么；
- Contract：输入、输出、状态与错误语义；
- Dependencies：依赖哪些模块 / 外部系统；
- Data：是否修改数据库 / 缓存 / 消息；
- Concurrency：是否涉及并发、锁、租约、幂等；
- Failure：失败、重试、恢复、降级行为；
- Test：验证哪些层级；
- Acceptance：什么条件下算完成；
- Documentation：哪些文档必须同步更新。

---

## 4. 架构与模块边界

推荐采用职责清晰的分层结构，具体名称可以根据语言和框架调整：

```text
API / Interface
      ↓
Application / Use Case
      ↓
Domain / Business Rules
      ↓
Execution / Runtime（需要时）
      ↓
Repository / Gateway
      ↓
Infrastructure
```

### 4.1 API / Interface 层

负责：

- HTTP / RPC / Event 协议适配；
- 参数解析；
- 请求鉴权入口；
- 状态码 / 协议错误映射；
- DTO / Schema 转换。

禁止：

- 复杂业务规则；
- 直接操作数据库实现业务流程；
- 直接编排多个基础设施；
- 在 Controller / Handler 内实现状态机。

### 4.2 Application / Service 层

负责：

- 用例编排；
- 业务流程；
- Domain Policy 调用；
- 事务边界；
- Repository / Gateway 协调。

禁止：

- 把所有职责塞入单一巨型 Service；
- 隐式创建数据库连接；
- 直接实现具体第三方 SDK 适配。

### 4.3 Domain 层

负责：

- 核心业务规则；
- 状态机；
- Policy；
- 不变量；
- 领域 Contract。

Domain 应尽量避免依赖具体 Web 框架、数据库驱动和第三方 SDK。

### 4.4 Runtime / Execution 层

仅在系统存在异步执行、Agent、Workflow、Scheduler、Worker、任务编排等场景时建立。

负责：

- 执行上下文；
- 调度与编排；
- 状态推进；
- Retry / Timeout；
- Checkpoint / Resume；
- 并发控制；
- Worker 生命周期。

禁止把 HTTP 协议适配混入 Runtime。

### 4.5 Infrastructure 层

负责：

- Database；
- Cache；
- Message Broker；
- Object Storage；
- HTTP Client；
- Model Provider；
- Embedding / Vector Store；
- 第三方 SDK。

Infrastructure 不拥有核心业务规则。

---

## 5. 领域模块化规则

### 5.1 按领域组织，而不是按文件类型无限平铺

推荐：

```text
services/
├── agent/
├── workflow/
├── scheduler/
├── knowledge/
├── execution/
└── identity/
```

不推荐长期演变为：

```text
services/
├── agent_service.py
├── workflow_service.py
├── scheduler_service.py
├── scheduler_helper.py
├── scheduler_utils.py
├── scheduler_manager.py
├── scheduler_handler.py
└── ...
```

### 5.2 子模块最小模板

```text
<domain>/
├── __init__ / index
├── contract
├── service
├── policy
├── repository
└── ...
```

只有存在真实职责时才增加文件。

禁止为了“看起来完整”机械创建：

```text
manager
handler
facade
helper
utils
```

---

## 6. Contract First

任何跨模块、跨进程、跨服务或跨前后端边界都必须建立明确 Contract。

Contract 至少应定义：

- 请求 / 输入结构；
- 响应 / 输出结构；
- 状态枚举；
- 错误码与错误语义；
- 幂等语义；
- 权限语义；
- Tenant / Scope 边界；
- 时间与时区规则；
- 版本兼容规则；
- 必填 / 可选字段。

### 6.1 ORM / 数据库模型不是 API Contract

```text
Database Model ≠ API Contract
API Schema ≠ Domain Model
Domain Model ≠ Provider Payload
```

必须显式进行边界转换。

### 6.2 Contract 变更原则

变更 Contract 时必须同步检查：

```text
API
 → Schema / DTO
 → Service
 → Database
 → Frontend / Consumer
 → Tests
 → Documentation
```

禁止只修改生产代码而不更新 Contract 和测试。

---

## 7. 数据库与数据一致性

### 7.1 Schema First

涉及持久化结构的功能必须遵循：

```text
设计数据模型
 ↓
Migration
 ↓
执行 Migration
 ↓
验证 Schema
 ↓
Repository
 ↓
Service
```

禁止直接修改线上数据库后再补 Migration。

### 7.2 事务边界

每个写操作必须明确：

- 哪些写入属于同一事务；
- 哪些操作允许最终一致；
- 哪些外部调用不能放在数据库事务内；
- 失败后如何恢复；
- 是否需要 Outbox / Event / Compensation。

### 7.3 数据事实优先

业务状态不能只依赖内存变量、日志或缓存推断。

需要恢复、审计或跨进程协作的关键状态必须持久化为可验证事实。

---

## 8. 幂等、并发与分布式一致性

企业级系统必须把并发行为当成正常路径，而不是异常情况。

### 8.1 幂等

涉及以下操作时必须明确幂等策略：

- 创建任务；
- 支付 / 订单；
- 消息消费；
- Workflow Resume；
- Scheduler Trigger；
- Worker Claim；
- 外部 Provider 调用；
- Webhook；
- 重试操作。

优先使用：

```text
业务唯一键
+ 数据库唯一约束
+ 原子检查 / 更新
```

而不是仅依赖进程内锁。

### 8.2 Lease / Lock / Fencing

涉及 Worker / Scheduler / 多实例执行时，应明确：

```text
Owner
Lease
Heartbeat
Expiration
Reclaim
Fencing
```

特别是 Worker 丢失 ownership 后，旧 Worker 不应继续推进业务状态。

### 8.3 Recovery

恢复流程必须区分：

```text
发现异常
 → 判断是否可恢复
 → 创建恢复动作
 → 幂等收敛
 → 新 Worker 接管
 → 继续执行
 → 记录结果
```

禁止用“重新跑一次”替代正式 Recovery Contract。

---

## 9. 状态机与生命周期

所有复杂生命周期必须显式定义状态机。

推荐：

```text
State
 ├── allowed transition
 ├── illegal transition
 ├── transition owner
 ├── persistence rule
 └── side effects
```

禁止通过多个 Service 各自修改同一状态字段。

状态推进必须有唯一权威入口，并明确：

- 谁可以推进；
- 哪些状态可以转换；
- 是否幂等；
- 并发时如何处理；
- 失败时状态是什么；
- 恢复后从哪里继续。

---

## 10. Scheduler / Worker / Runtime 通用原则

对于异步执行系统，建议冻结以下职责：

```text
Scheduler
    = 什么时候检查 / 触发

Recovery Policy
    = 是否允许恢复

Recovery Domain
    = 如何安全创建恢复动作

Worker
    = 谁获得执行权

Lease / Fencing
    = 谁仍然拥有执行权

Runtime
    = 如何实际执行

Checkpoint
    = 已经发生了什么

Recovery
    = 如何从持久化事实继续
```

### 禁止职责混合

- Scheduler 不直接承担完整业务执行；
- Worker 不负责决定业务恢复策略；
- Runtime 不直接决定 HTTP API Contract；
- Recovery 不复制 Worker Claim / Lease 状态机；
- Provider 不承担业务状态机；
- Telemetry 不改变业务状态。

---

## 11. 外部 Provider / Adapter 规则

同一种外部能力只能有一个正式 Provider 适配入口。

推荐：

```text
Domain Service
      ↓
Stable Contract
      ↓
Provider Interface
      ↓
Provider Implementation
      ↓
External SDK / HTTP
```

禁止：

```text
Service A → Provider A
Service B → Provider B
Service C → SDK 直接调用
```

切换模型、数据库、消息队列或第三方服务时，只允许替换 Infrastructure 适配，不应迫使业务领域复制实现。

---

## 12. AI Agent 专项原则

对于 Agent / LLM / Tool / RAG 系统，额外遵守：

### 12.1 Model Provider 与业务解耦

```text
Agent / Domain
      ↓
LLM Contract
      ↓
Provider Adapter
      ↓
Model Provider
```

禁止业务代码到处出现具体模型 SDK 调用。

### 12.2 Prompt 不是隐藏代码

关键 Prompt 应具备：

- 版本；
- 用途；
- 输入 Contract；
- 输出 Contract；
- 约束；
- 失败处理；
- 测试样例。

### 12.3 Tool 必须有边界

每个 Tool 应明确：

- 输入 Schema；
- 输出 Schema；
- 权限；
- Tenant Scope；
- 超时；
- Retry；
- 幂等；
- Side Effect；
- 审计要求。

### 12.4 Agent 不应直接拥有基础设施权限

Agent / LLM 输出必须经过：

```text
Model Output
 ↓
Schema Validation
 ↓
Policy / Permission
 ↓
Tool Authorization
 ↓
Tool Execution
```

禁止把未经验证的模型文本直接作为高权限系统命令执行。

---

## 13. 测试体系

测试实现与测试编排必须分离。

推荐：

```text
tests/
├── unit/
├── integration/
├── contract/
├── api/
├── e2e/
└── evaluation/

scripts/test/
├── unit/
├── integration/
├── contract/
├── release/
└── e2e/
```

### 13.1 测试层级

```text
Unit
 ↓
Integration
 ↓
Contract / API
 ↓
Real Integration
 ↓
E2E
```

不同项目可以裁剪，但必须明确每层解决什么问题。

### 13.2 测试必须验证行为

优先验证：

```text
输入
状态
持久化事实
输出
异常
并发
幂等
权限
```

而不是只验证内部实现细节。

### 13.3 测试脚本必须可重复

测试 Gate 必须：

- 不要求手工修改代码；
- 明确工作目录；
- 明确依赖；
- 明确环境变量；
- 明确前置服务；
- 明确失败条件；
- 明确退出码；
- 明确“未执行 / 失败 / 通过”。

### 13.4 真实链路测试

只要任务涉及真实数据库、Provider、HTTP、消息或 Runtime 生命周期，就必须在适当阶段提供真实链路验证。

Mock 只能解决隔离测试问题，不能代替真实系统验收。

---

## 14. 测试 Gate 设计

推荐将 Gate 按职责隔离：

```text
Backend / Core Gate
    = 核心业务 + 数据 + Contract

Frontend Gate
    = UI + Frontend Contract

E2E Gate
    = 用户真实链路

Release Gate
    = 发布级综合验证
```

禁止一个脚本无限调用所有测试，导致：

- 失败原因不可定位；
- 工作目录混乱；
- 环境依赖互相污染；
- 单项验证无法重复执行。

项目可以根据成熟度决定哪些 Gate 由本地执行、哪些由 CI 执行，但必须保持 Gate 职责独立。

---

## 15. 错误处理与故障恢复

错误必须分层：

```text
Validation Error
Domain Error
Permission Error
Not Found
Conflict / Idempotency
Infrastructure Error
Provider Error
Timeout
Cancellation
Recovery Error
```

### 15.1 错误语义必须稳定

调用者需要知道：

- 是否可以重试；
- 是否需要修改输入；
- 是否已经产生副作用；
- 是否需要人工介入；
- 是否可以安全恢复。

### 15.2 错误必须沉淀

已经发生并完成分析的工程错误，应形成可搜索的 Error / Incident / ADR 记录：

```text
现象
 → 原因
 → 影响
 → 修复
 → 防止复发措施
```

禁止同类问题反复依赖口头记忆。

---

## 16. 可观测性

生产系统至少需要：

```text
Logs
Metrics
Traces
Audit
```

### 16.1 Trace

跨 Scheduler → Recovery → Worker → Runtime → Provider 的链路应保持 Trace lineage。

推荐：

```text
Parent Trace
    ↓
Child Trace
    ↓
Durable Trace Link
    ↓
Worker / Runtime
```

### 16.2 Telemetry 不得泄露业务敏感数据

日志 / Trace 默认禁止写入：

- Secret；
- API Key；
- Password；
- Token；
- Provider Credential；
- 完整 Prompt；
- 完整业务 Payload；
- 大型 Checkpoint state。

只记录诊断所需的最小字段。

---

## 17. 安全与租户隔离

所有企业级功能都应默认考虑：

```text
Authentication
Authorization
Tenant Isolation
Data Scope
Secret Management
Audit
Rate Limit
Input Validation
Output Validation
```

### Tenant Boundary

Tenant Scope 必须在服务边界和数据访问边界同时存在。

禁止：

```text
先查询全部数据
再在业务层过滤 tenant_id
```

优先让 Repository / Query 本身带有 Tenant Scope。

### Secret

禁止提交：

- API Key；
- Password；
- Access Token；
- Private Key；
- Provider Credential。

本地配置、开发配置、CI Secret、生产 Secret 必须有明确边界。

---

## 18. 配置管理

配置应分为：

```text
代码默认值
开发环境配置
测试环境配置
生产环境配置
Secret
```

原则：

- 无 Secret 的安全默认值可以进入仓库；
- Secret 必须来自环境变量或 Secret Manager；
- 配置必须经过 Schema / 类型校验；
- Provider endpoint、model、timeout 等运行配置不能散落在业务代码；
- 不同环境的差异必须显式可见。

---

## 19. 代码规范与注释

### 19.1 命名

命名优先表达业务语义：

```text
claim_execution
renew_lease
resume_execution
merge_branch_state
```

避免：

```text
do_it
process_data
handle
manager
helper
```

### 19.2 中文职责说明

对于团队以中文为主要工程语言的项目，公共模块、类、复杂函数应使用统一中文说明。

说明重点是：

```text
做什么
不做什么
为什么这样做
参数
返回值
异常 / 副作用
事务 / 并发边界
```

不是机械重复函数名。

### 19.3 非显然规则必须说明原因

涉及以下规则时必须解释“为什么”：

- 时间槽；
- misfire；
- lease；
- fencing；
- 幂等；
- 权限；
- tenant boundary；
- 状态机；
- Retry；
- 降级；
- Provider compatibility。

---

## 20. Git 与提交策略

### 20.1 分支策略可配置

通用默认建议：

```text
main
 ├── feature/*
 ├── fix/*
 └── refactor/*
```

生产级项目建议保护 `main`，通过 PR / Review / CI Gate 合入。

如果某个项目明确采用“所有开发直接基于 main”的策略，则必须在项目专属治理文档中显式声明，不能把该策略误认为通用规则。

### 20.2 原子提交

一个提交应表达一个完整工程事实：

```text
功能代码
+ 必要测试
+ 对应 Migration
+ 对应 Contract
+ 对应文档
```

禁止：

```text
先提交半成品代码
再提交测试
再提交文档
再提交错误记录
```

除非这些步骤本身具有独立工程意义。

### 20.3 Commit Message

推荐：

```text
feat(scope): ...
fix(scope): ...
refactor(scope): ...
test(scope): ...
docs(scope): ...
chore(scope): ...
```

提交说明应回答：

```text
改了什么
为什么改
```

---

## 21. Code Review

Review 不应只检查“代码能不能运行”，还必须检查：

### 架构

- 是否创建重复能力；
- 是否违反模块边界；
- 是否出现循环依赖；
- 是否把 Infrastructure 泄漏到 Domain；
- 是否把业务规则放进 API / Provider。

### 数据

- Migration 是否完整；
- 事务边界是否正确；
- 并发是否安全；
- 幂等是否明确；
- Tenant Scope 是否完整。

### Runtime

- Retry / Timeout；
- Cancellation；
- Lease / Ownership；
- Recovery；
- Checkpoint；
- 状态机。

### 安全

- Secret；
- 权限；
- 输入校验；
- 敏感日志；
- 外部调用边界。

### 测试

- 是否覆盖正常路径；
- 边界条件；
- 异常；
- 并发；
- 幂等；
- 真实链路。

---

## 22. 文档治理

建议建立：

```text
docs/
├── 00-architecture/
├── 01-governance/
├── 02-phases/
├── 03-acceptance/
├── 04-errors/
└── PROJECT_STATUS.md
```

### 文档职责

| 文档 | 负责内容 |
|---|---|
| Architecture | 长期架构、边界、数据流、模块职责 |
| Governance | 开发、测试、提交、安全、Review 规则 |
| Phase | 当前阶段目标与实现范围 |
| Acceptance | 可执行验收条件与实际结果 |
| Error | 工程错误与修复经验 |
| Status | 当前项目真实状态 |

### 状态真实性

禁止记录未经执行的测试为“通过”。

状态必须区分：

```text
未开始
开发中
阻塞
实现完成
测试通过
验收通过
正式关闭
```

---

## 23. 重构规则

重构首先定义目标结构，再执行迁移。

标准流程：

```text
目标架构
 ↓
迁移矩阵
 ↓
建立目标模块
 ↓
迁移实现
 ↓
修改所有调用方
 ↓
修改所有测试
 ↓
删除旧实现
 ↓
全仓搜索旧路径
 ↓
重复实现检查
 ↓
测试 Gate
 ↓
文档更新
```

### 业务不变原则

纯架构重构默认不得改变：

- API Path；
- HTTP Method；
- Request / Response Contract；
- 权限行为；
- Tenant Isolation；
- 数据事实；
- Runtime 行为；
- Provider 行为；
- 错误语义。

如果必须改变业务行为，应将其拆分为独立设计变更，而不是隐藏在重构中。

---

## 24. 性能与可靠性

性能优化必须基于测量，而不是猜测。

标准流程：

```text
Baseline
 ↓
Measure
 ↓
Identify bottleneck
 ↓
Optimize
 ↓
Measure again
 ↓
Verify no regression
```

可靠性设计至少考虑：

- Timeout；
- Retry；
- Backoff；
- Circuit Breaker；
- Rate Limit；
- Queue Backpressure；
- Connection Pool；
- Resource Limit；
- Graceful Shutdown；
- Recovery。

禁止无限 Retry、无限 Queue、无限并发。

---

## 25. API / Frontend 开发原则

前后端必须围绕稳定 Contract 协作：

```text
Backend Contract
      ↓
Frontend API Types
      ↓
UI / State
```

推荐开发顺序：

```text
Backend Contract
 ↓
Backend implementation
 ↓
Backend tests
 ↓
Frontend types
 ↓
Frontend implementation
 ↓
Frontend tests
 ↓
E2E
```

前端不得自行猜测后端字段、状态或错误语义。

---

## 26. Definition of Done

一个功能只有同时满足以下条件才允许标记完成：

- [ ] 需求边界明确；
- [ ] 架构边界明确；
- [ ] Contract 已定义；
- [ ] 已检查并复用现有能力；
- [ ] 生产代码完成；
- [ ] 数据库 Migration 完成（如需要）；
- [ ] 单元测试完成；
- [ ] 集成 / Contract 测试完成（如需要）；
- [ ] 真实链路验证完成（如需要）；
- [ ] 并发 / 幂等 / Recovery 验证完成（如适用）；
- [ ] 安全检查完成；
- [ ] 可观测性完成；
- [ ] 文档更新；
- [ ] Error / Incident 记录更新（如发生）；
- [ ] Code Review 完成；
- [ ] Git 提交为完整原子交付单元。

---

## 27. 新项目初始化模板

新项目可以直接采用以下治理骨架：

```text
project/
├── docs/
│   ├── 00-architecture/
│   ├── 01-governance/
│   │   └── DEVELOPMENT.md
│   ├── 02-phases/
│   ├── 03-acceptance/
│   ├── 04-errors/
│   └── PROJECT_STATUS.md
├── backend/ / server/ / services/
├── frontend/ / web/
├── scripts/
├── tests/
└── README.md
```

项目专属 `DEVELOPMENT.md` 应至少定义：

1. 技术栈；
2. 目录结构；
3. 本地运行方式；
4. 测试命令；
5. Gate；
6. 分支策略；
7. Commit 规范；
8. Secret 管理；
9. 数据库 Migration；
10. 文档更新规则。

---

## 28. 新功能标准工作流

```text
① 同步最新代码基线
        ↓
② 阅读 Governance / Architecture / Status
        ↓
③ 搜索已有实现，避免重复能力
        ↓
④ 明确 Domain / Scope / Contract
        ↓
⑤ 设计数据模型与状态机
        ↓
⑥ Migration（如需要）
        ↓
⑦ Domain / Service / Repository
        ↓
⑧ Runtime / Provider（如需要）
        ↓
⑨ API / Event Contract
        ↓
⑩ Unit / Integration / Contract Test
        ↓
⑪ Real API / Runtime 验证
        ↓
⑫ Frontend / Consumer
        ↓
⑬ E2E（如范围需要）
        ↓
⑭ Security / Observability Review
        ↓
⑮ 更新 Phase / Acceptance / Status / Error
        ↓
⑯ Code Review
        ↓
⑰ 原子提交
```

---

## 29. 禁止事项清单

以下行为默认禁止，除非项目治理文档明确批准并记录原因：

1. 未同步基线直接开发；
2. 重复创建已有业务能力；
3. 用 `utils` / `helper` 隐藏业务设计问题；
4. API Handler 直接实现复杂业务；
5. Domain 直接依赖第三方 SDK；
6. 多个 Provider 实现同一外部能力；
7. 多个模块修改同一状态机；
8. 没有 Migration 就修改数据库结构；
9. 用 Mock 代替所有真实链路验证；
10. 未执行测试却记录 PASS；
11. 把 Secret 提交到 Git；
12. 日志记录完整 Prompt / Token / Credential；
13. 用无限 Retry 解决不稳定外部依赖；
14. 用兼容垫片长期掩盖迁移未完成；
15. 在没有业务理由的情况下复制生产算法到测试；
16. 用一次性脚本代替正式 Runtime / Recovery；
17. 用文档描述“已经完成”却没有对应代码 / 测试 / 证据；
18. 在重构任务中夹带未经设计评审的业务行为变更。

---

## 30. 本准则与具体项目治理的关系

本文件是**通用上位模板**，具体项目必须将其落地为项目可执行规则。

建议关系：

```text
UNIVERSAL_DEVELOPMENT_GUIDELINES.md
                ↓
        项目专属 DEVELOPMENT.md
                ↓
      Architecture / Phase / Acceptance
                ↓
          实际代码与测试
```

项目专属规则可以比本文件更严格，但不应无明确原因降低以下核心要求：

```text
单一事实源
明确模块边界
Contract First
Migration 可追踪
幂等与并发安全
真实测试证据
Secret 安全
可观测性
错误沉淀
原子交付
文档与代码同步
```

---

## 31. 快速检查表

### 开发前

- [ ] 已同步最新基线
- [ ] 已读取治理规则
- [ ] 已读取当前架构与状态
- [ ] 已搜索已有实现
- [ ] 已确定 Domain 边界
- [ ] 已确定 Contract

### 开发中

- [ ] 没有创建重复能力
- [ ] 模块职责清晰
- [ ] 数据变更有 Migration
- [ ] 状态机只有唯一写入口
- [ ] 幂等策略明确
- [ ] 并发 / Lease / Fencing 已考虑
- [ ] Provider 与业务解耦
- [ ] Secret 未进入代码
- [ ] 日志不泄露敏感数据

### 提交前

- [ ] Unit Test
- [ ] Integration / Contract Test
- [ ] Real API / Runtime Test（适用时）
- [ ] E2E（适用时）
- [ ] Security Review
- [ ] Observability Review
- [ ] Error Record
- [ ] Acceptance 更新
- [ ] Status 更新
- [ ] Commit 原子且可解释

---

## 32. 版本与维护

本准则应作为长期工程资产维护。

当某个项目发生以下事件时，应评估是否需要反向沉淀为通用规则：

- 发现重复架构问题；
- 发生生产级故障；
- 新增稳定的并发 / Recovery 模式；
- 新增安全约束；
- 新增统一测试 Gate；
- 新增 Agent / Provider / Tool 治理模式；
- 发现现有规则存在明显缺口。

通用规则只有在**至少具有跨项目复用价值**时才进入本文件；项目特有的业务规则、技术参数和历史背景应保留在项目专属文档中。
