# Backend 模块架构与开发模板

## 1. 目的

本文件定义 Backend 的长期模块边界、目录模板、依赖方向和新功能开发模板，作为后续项目复用的工程模板。

本模板基于当前 `main` 的实际 FastAPI 项目结构演进而来。历史代码迁移必须完成真实模块重构，不允许通过兼容垫片长期保留旧目录或旧实现。

## 2. 标准目录

```text
backend/
├── app/
│   ├── api/                    # HTTP / API 协议适配
│   │   └── v1/<domain>/
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
| `services` | 领域业务规则、Policy、Repository 编排 | 不把 Runtime、Infrastructure 混入领域业务 |
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
│   ├── __init__.py
│   ├── embedding.py
│   └── ...
└── http/
```

Repository 必须属于对应业务领域，不进入 `infrastructure/db/`；数据库 Session、Transaction 等技术能力属于 Infrastructure。

Provider 必须集中在 `infrastructure/providers/`。同一外部能力只能有一个正式技术适配实现；业务 Service 只能依赖稳定 Contract，禁止在 `services/` 再复制 Provider。

## 8. 模块说明与注释规则

每个新增或重构的 Python 模块必须在文件顶部提供简短中文模块说明，至少说明：

```text
模块职责
边界 / 不负责什么
关键外部依赖（存在时）
```

类、公共方法和复杂算法只在需要时补充中文 docstring/comment，解释业务意图、约束或技术原因。禁止使用无意义的“初始化服务”“处理数据”等空洞注释，也禁止用大量注释掩盖职责混乱。

测试模块同样应通过模块级 docstring 说明测试对象与验证范围。

## 9. Middleware 与 Dependencies 边界

```text
middleware
    = HTTP 请求生命周期横向处理

dependencies
    = FastAPI Handler 依赖注入与请求上下文
```

二者禁止合并为通用工具层。

## 10. Utils 使用规则

`utils/` 只能放没有领域语义的通用纯工具，例如时间、ID、JSON 等。

以下内容必须放回对应领域：

```text
agent_utils.py       → services/agent/
knowledge_utils.py   → services/knowledge/
workflow_utils.py    → services/workflow/
scheduler_utils.py   → services/scheduler/
```

## 11. 新功能标准开发模板

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

开发过程中必须先检查是否已经存在同一能力；禁止为了新功能方便而新增第二个 Service、Provider、Repository、Runtime 或工具实现。

## 12. Contract 规则

后端 Contract 是前后端唯一业务契约。

```text
HTTP Schema
    ↓
Domain Contract
    ↓
Service
```

ORM Model 不得直接成为前后端业务契约。

## 13. 测试模板

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
└── module-refactor/
```

Backend 根测试目录不得新增 `test_*.py`。

## 14. 数据与外部资源规则

线上业务数据必须通过 Repository / Infrastructure 访问真实 PostgreSQL / Redis / Provider。

Evaluation 数据集、Baseline、Result 可以使用版本化 JSON / JSONL，但不得反向充当线上业务数据库。

## 15. 完全重构原则

目录重构必须是完整重构，不允许使用垫片、代理文件、旧入口转发或双实现掩盖迁移未完成。

每个领域迁移必须同时完成：

1. 建立目标领域子模块；
2. 按职责拆分 Service / Repository / Contract / Runtime；
3. 修改所有生产代码 import；
4. 修改所有测试 import；
5. 删除旧文件；
6. 全仓搜索并清除旧模块路径；
7. 检查重复实现；
8. 为新增/重构模块补充必要职责说明；
9. 执行对应测试 Gate；
10. 更新迁移矩阵、Phase、Acceptance、Status 与必要的 Error 记录。

只有以上步骤全部完成，该领域才允许标记为“迁移完成”。迁移期间可以在一个原子提交中完成文件新增、调用方切换和旧文件删除，但不得留下兼容实现。

## 16. 业务不变原则

目录重构不得改变既有业务行为：

```text
API Path 不变
HTTP Method 不变
Request / Response Contract 不变
权限行为不变
Tenant Isolation 不变
数据库模型与 Migration 不变
Runtime 行为不变
Provider 行为不变
错误语义不变
```

允许改变的仅是：

```text
文件位置
模块边界
import 路径
内部职责组织
```

如果为了完成目录重构发现必须改变业务行为，必须先暂停迁移并单独形成设计变更。

## 17. 迁移验收模板

每个领域完成后必须执行：

```text
① 领域单元 / 集成测试
② API Contract（涉及 API 时）
③ 全仓旧 import 搜索
④ 目标目录结构检查
⑤ 重复实现检查
⑥ Backend Regression
⑦ Alembic head/current（仅当任务涉及数据库时）
⑧ Real API Gate（范围需要时）
⑨ 更新 Phase / Acceptance / Status / Error
```

测试结果只能记录本地实际执行结果，禁止预填通过。

## 18. 当前项目参考实现

当前 `services/workflow_scheduler/` 已采用领域子模块方式，并通过 `__init__.py` 暴露稳定入口；内部已经拆分 Contract、模型、时间、lease、misfire、Repository、Runtime。该结构可作为职责拆分参考，但后续重构必须遵守本文件第 15 节的完全重构原则。

当前 Knowledge Provider 已完成从 `services` 到 `infrastructure/providers` 的物理迁移，可作为“领域业务 + 技术适配分离且无重复实现”的参考实现。
