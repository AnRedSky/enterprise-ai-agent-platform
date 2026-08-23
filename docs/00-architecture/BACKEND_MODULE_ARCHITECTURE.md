# Backend 模块架构与开发模板

## 1. 目的

本文件定义 Backend 的长期模块边界、目录模板、依赖方向和新功能开发模板，作为后续项目复用的工程模板。

本模板基于当前 `main` 的实际 FastAPI 项目结构演进而来，不要求一次性重构所有历史代码；历史代码按迁移矩阵逐步收敛。

## 2. 标准目录

```text
backend/
├── app/
│   ├── api/                    # HTTP / API 协议适配
│   │   └── v1/
│   │       └── <domain>/
│   ├── core/                   # 应用核心能力
│   ├── dependencies/           # FastAPI 依赖注入
│   ├── middleware/             # HTTP 横向中间件
│   ├── models/                 # ORM 持久化模型
│   ├── schemas/                # API Request / Response / DTO
│   ├── services/               # 领域业务模块
│   │   └── <domain>/
│   ├── runtime/                # 执行与运行时编排
│   ├── infrastructure/         # 外部技术基础设施
│   │   ├── db/
│   │   ├── redis/
│   │   ├── providers/
│   │   └── http/
│   ├── utils/                  # 无业务语义的通用工具
│   └── main.py
├── models/                     # 若项目需要独立共享 ORM 基础设施，可按项目约定保留；当前项目以 app/models 为准
├── scripts/
├── tests/
└── ...
```

## 3. 模块职责

| 模块 | 职责 | 禁止事项 |
|---|---|---|
| `api` | 路由、HTTP 协议适配、状态码与鉴权入口 | 不承载业务规则、直接操作 ORM |
| `core` | 配置、安全、全局异常、日志等应用核心能力 | 不放具体业务领域实现 |
| `dependencies` | FastAPI DI、请求用户、租户、数据库 Session 等上下文 | 不实现业务流程 |
| `middleware` | Request/Response 生命周期、Request ID、横向错误处理等 | 不承载领域业务规则 |
| `models` | SQLAlchemy ORM 持久化模型 | 不作为 API Contract |
| `schemas` | API 输入输出与 DTO | 不替代领域 Service Contract |
| `services` | 领域业务规则、Policy、Repository 编排 | 不把所有 Runtime 代码堆入 Service 根目录 |
| `runtime` | Agent/Workflow/Trigger 等执行编排 | 不直接承担 HTTP 协议适配 |
| `infrastructure` | DB、Redis、外部 Provider、HTTP 等技术适配 | 不放领域业务规则 |
| `utils` | 与业务无关的纯工具 | 禁止建立 `xxx_utils.py` 业务垃圾桶 |

## 4. 分层方向

```text
API
 ↓
Dependencies / Context
 ↓
Service
 ↓
Runtime（需要执行编排时）
 ↓
Gateway / Tool / Memory / Knowledge
 ↓
Repository
 ↓
ORM Model
 ↓
Infrastructure DB / Redis / External Provider
```

Service 与 Runtime 不强制每个领域同时存在；只有实际存在对应职责时才建立模块。

## 5. 领域模块模板

新业务领域统一从以下最小模板开始：

```text
services/<domain>/
├── __init__.py                 # 稳定公开入口
├── contract.py                 # 领域边界；需要时建立
├── service.py                  # 业务规则；需要时建立
├── repository.py               # 持久化访问；需要时建立
└── ...                         # 按真实职责拆分
```

复杂领域可以进一步拆分：

```text
services/<domain>/
├── __init__.py
├── contract.py
├── policy.py
├── definition.py
├── execution.py
├── repository.py
└── ...
```

禁止为了形式强制创建 `manager.py`、`handler.py`、`facade.py`、`helper.py` 等没有独立职责的文件。

## 6. Runtime 模板

```text
runtime/
├── agent/
├── workflow/
├── trigger/
└── ...
```

Runtime 只负责执行、状态推进、编排和运行时上下文；领域业务规则留在 `services/<domain>/`。

## 7. Infrastructure 模板

```text
infrastructure/
├── db/
│   ├── session.py
│   ├── transaction.py
│   └── types.py
├── redis/
├── providers/
└── http/
```

Repository 不进入 `infrastructure/db/`；Repository 属于对应业务领域，数据库 Session/Transaction 等技术能力属于 Infrastructure。

## 8. Middleware 与 Dependencies 边界

```text
middleware
    = HTTP 请求生命周期横向处理

dependencies
    = FastAPI Handler 依赖注入与请求上下文
```

二者禁止合并为通用工具层。

## 9. Utils 使用规则

`utils/` 只能放没有领域语义的通用纯工具，例如时间、ID、JSON 等。

以下内容必须放回对应领域：

```text
agent_utils.py       → services/agent/
knowledge_utils.py   → services/knowledge/
workflow_utils.py    → services/workflow/
scheduler_utils.py   → services/scheduler/
```

## 10. 新功能标准开发模板

```text
① 需求与架构确认
    ↓
② 确定 Domain 边界
    ↓
③ 定义 Backend Contract
    ↓
④ 建立 services/<domain>/ 子模块
    ↓
⑤ 如涉及数据库：先建立 Alembic Migration
    ↓
⑥ 实现 Repository / Service
    ↓
⑦ 如涉及执行：实现 Runtime
    ↓
⑧ 实现 API Schema + API Router
    ↓
⑨ Backend Unit / Integration / API Contract
    ↓
⑩ Real API Gate（范围需要时）
    ↓
⑪ Frontend API Types / UI
    ↓
⑫ Frontend Gate / E2E（范围需要时）
    ↓
⑬ 更新 Phase / Acceptance / Status / Error
    ↓
⑭ 直接提交 main
```

## 11. Contract 规则

后端 Contract 是前后端唯一业务契约。

```text
HTTP Schema
    ↓
Domain Contract
    ↓
Service
```

ORM Model 不得直接成为前后端业务契约。

## 12. 测试模板

测试实现与测试编排严格分离：

```text
backend/tests/
├── unit/
├── integration/
├── api_contract/
└── api_real/

backend/scripts/test/
├── release/
├── api-real/
├── integration/
└── ...
```

Backend 根测试目录不得新增 `test_*.py`。

## 13. 数据与外部资源规则

线上业务数据必须通过 Repository / Infrastructure 访问真实 PostgreSQL / Redis / Provider。

Evaluation 数据集、Baseline、Result 可以使用版本化 JSON / JSONL，但不得反向充当线上业务数据库。

## 14. 迁移原则

历史代码不进行机械批量重命名。迁移必须：

1. 先建立映射矩阵；
2. 分领域迁移；
3. 调整 import 与测试；
4. 必要时保留薄兼容入口；
5. 静态检查旧路径；
6. 执行对应 Backend Gate；
7. 不因纯目录迁移创建数据库 Migration。

## 15. 当前项目作为模板的参考实现

当前 `services/workflow_scheduler/` 已采用领域子模块方式，并通过 `__init__.py` 暴露稳定入口；内部已经拆分 Contract、模型、时间、lease、misfire、Repository、Runtime。这一组织方式作为后续领域模块化的参考实现。
