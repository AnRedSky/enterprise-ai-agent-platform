# Backend scripts 目录规范

`backend/scripts` 只保存可重复执行的工程脚本，按**用途**分类，不按业务代码堆放。

## 目录职责

```text
scripts/
├── test/
│   ├── api-real/       # Real API 自动化测试唯一编排入口
│   ├── integration/    # 前后端联调 Gate
│   └── regression/     # 项目阶段性完整回归入口
├── migration/          # Alembic 数据库迁移
├── evaluation/
│   ├── knowledge/      # Knowledge/RAG 质量评估
│   └── embedding/      # Embedding Provider 专项评估
└── dev/                # 开发辅助脚本，不作为正式验收 Gate
```

数字前缀只表示同一目录内的执行顺序，不代表 Phase 编号。

## 唯一测试编排原则

```text
tests/          = 测试实现与断言
scripts/test/   = 测试编排
```

禁止在多个脚本中复制登录、Token、Workflow Fixture、API 断言或同一数据库前置逻辑。

### Real API

前后端联调前必须执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

该入口调用现有 bootstrap，自动完成真实 HTTP 注册/登录、Workflow/Execution 准备和临时上下文清理；开发人员禁止手工填写 `ACCESS_TOKEN`、`WORKFLOW_ID`、`WORKFLOW_EXECUTION_ID`。

### Integration

`integration` 只负责调用已经存在的 Unit/Contract/Real API/Frontend Gate，不复制测试逻辑。Real API Gate 未通过时必须立即停止联调。

### Regression

`regression` 是项目阶段性总入口；它可以编排多个已存在入口，但每个测试实现只能有一个归属位置。

### Evaluation / Migration

Evaluation 是质量评估程序，不是 pytest 单元测试；Migration 只负责数据库迁移。二者不得混入测试目录。

## 迁移规则

根目录历史脚本属于待治理遗留项。新增脚本禁止放在 `backend/scripts` 根目录；迁移完成后删除旧入口，并同步修正文档中的调用路径。
