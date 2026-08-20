# Backend scripts 目录规范

`backend/scripts` 只保存可重复执行的工程脚本，按**用途**分类，不按业务代码堆放。

## 目录职责

```text
scripts/
├── api-real/       # 真实 HTTP API 自动化测试入口及测试前置条件
├── migration/      # 数据库迁移/版本管理
├── integration/    # 前后端自动化联调 Gate
├── knowledge/      # Knowledge 专项评估/场景脚本
└── embedding/     # Embedding Provider 专项验证
```

同一类脚本使用数字前缀表示执行顺序。数字只表示**编排顺序**，不代表 Phase 编号。

## Real API 测试唯一入口

前后端联调前必须先执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\api-real\01_run_real_api_tests.ps1
```

该入口负责：

1. `00_bootstrap_real_api.py` 自动通过真实 HTTP API 完成注册/登录；
2. 自动发现或创建已发布 Workflow；
3. 自动创建 Workflow Execution；
4. 将短生命周期的 Token/ID 写入临时 context；
5. 统一执行 `tests/api_real -m real_api`；
6. finally 中清理 Token、ID 和临时 context。

**禁止**要求开发人员手工填写 `ACCESS_TOKEN`、`WORKFLOW_ID`、`WORKFLOW_EXECUTION_ID`。

## 测试职责边界

- `tests/`：测试实现。
- `scripts/api-real/`：真实 API 测试的前置条件与统一编排，不重复实现 API 断言。
- `scripts/integration/`：联调 Gate，只调用已经存在的测试入口，不复制 API 测试逻辑。
- `scripts/migration/`：只负责迁移。

新增真实 API 覆盖时，优先新增/扩展 `tests/api_real/`，再由统一入口执行；禁止新增一个脚本复制一套登录、Token、Workflow Fixture 创建逻辑。
