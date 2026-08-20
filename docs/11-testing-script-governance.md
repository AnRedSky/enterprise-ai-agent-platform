# 测试脚本治理准则

## 1. Main 基线

所有开发、修复、测试脚本整改均以最新 `main` 为基线。不得为了测试目的创建临时开发分支；修正直接提交 `main`。

## 2. 测试层级

```text
单元/契约测试
    ↓
数据库迁移验证
    ↓
真实 HTTP API 自动化测试（强制 Gate）
    ↓
前后端自动化联调
    ↓
浏览器/人工场景验收
```

未通过真实 API Gate，不得进入前后端联调。

## 3. API 真实调用测试

真实 API 测试实现统一放在 `backend/tests/api_real/`；脚本统一放在 `backend/scripts/api-real/`。

脚本使用数字前缀表达顺序：

- `00_bootstrap_real_api.py`：只负责测试前置数据与认证上下文准备。
- `01_run_real_api_tests.ps1`：唯一真实 API Gate，负责调用 bootstrap 后统一运行全部 `tests/api_real`。

禁止重新编写登录、Token、Workflow、Execution Fixture 创建逻辑形成新的重复脚本。

Token、Workflow ID、Execution ID 必须由测试前置脚本通过真实 HTTP API 自动取得，禁止要求开发人员手工填写。

## 4. 脚本职责

脚本必须按用途归类：

- `api-real/`：真实 HTTP API。
- `migration/`：数据库迁移。
- `integration/`：前后端联调 Gate。
- `knowledge/`：知识库专项验证。
- `embedding/`：Embedding Provider 专项验证。

脚本只负责编排，不复制测试断言。API 断言统一进入 `tests/api_real/`。

## 5. 防止冗余

新增 API 测试场景时：

1. 先搜索 `tests/api_real/` 是否已有覆盖；
2. 优先扩展现有测试模块；
3. 只有测试职责完全不同才新增测试文件；
4. 不新增第二套认证/Fixture Bootstrap；
5. 不新增第二个 Real API Gate；
6. 联调 Gate 只能调用 canonical Real API Gate。
