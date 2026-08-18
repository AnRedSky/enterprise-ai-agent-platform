# 39 - Phase 23 手工测试执行与反馈指南

## 1. 测试模式调整

由于当前开发环境无法稳定直接访问 GitHub 仓库并执行完整依赖环境，本项目从本阶段开始将“本地测试执行”改为由开发者/项目负责人在本地环境手工执行并反馈结果。

本文件是唯一的反馈入口规范。测试通过必须以实际命令输出为依据，不允许仅以代码存在作为通过依据。

## 2. 测试前提

### Backend

```bash
cd backend
python --version
pip install -r requirements.txt
pytest --version
```

如果项目使用 Docker/PostgreSQL/Redis，请先按照项目启动文档启动依赖。

### Frontend

```bash
cd frontend
node --version
npm --version
npm install
```

## 3. Frontend 测试

执行：

```bash
npm test
```

必须反馈：

- 命令完整输出
- 测试文件数量
- Test case 数量
- passed / failed 数量
- 首个失败用例完整错误堆栈

然后执行：

```bash
npm run build
```

反馈：

- 是否成功
- TypeScript / vue-tsc 错误
- Vite build 错误
- 最终生成结果

## 4. Backend 全量测试

执行：

```bash
cd backend
pytest -q
```

反馈：

```text
PASS/FAIL
passed=
failed=
skipped=
errors=
```

失败时必须提供首个失败测试的完整 traceback。

## 5. HTTP RBAC 专项测试

优先执行：

```bash
pytest -q tests/test_runtime_http_rbac.py
pytest -q tests/test_runtime_rbac_matrix.py
```

验收矩阵：

| 场景 | 期望 |
|---|---:|
| 无认证访问 Runtime | 401 |
| Owner 查询自己的资源 | 200 |
| Owner 查询其他 Owner Execution | 404 |
| Owner 查询其他 Owner Timeline | 404 |
| Admin 跨 Owner 查询 | 200 |
| status filter | 正确过滤 |
| agent_id filter | 正确过滤 |
| trace_id filter | 正确过滤 |
| request_id filter | 正确过滤 |
| Audit Owner Scope | 不越权 |
| Audit Admin Scope | 可跨 Owner |
| Pagination | page/page_size/total 正确 |

## 6. API 手工验证

启动 Backend：

```bash
uvicorn app.main:app --reload --port 8000
```

打开：

```text
http://localhost:8000/docs
```

使用实际测试账号分别验证：

1. 未登录 Token。
2. 普通 Owner 用户。
3. Admin 用户。
4. 不同 Owner 的 Agent / Session / Execution。
5. Runtime Filter。
6. Audit Log Filter。

禁止在反馈中提交真实密码、API Key、JWT 完整 Token 或其他秘密信息。

## 7. Git / 文件污染检查

测试结束执行：

```bash
git status --short
git diff --stat
```

确认没有：

- `node_modules/`
- `dist/`
- `coverage/`
- `.env`
- 密钥
- 日志
- IDE 临时文件
- 个人文件

## 8. 反馈模板

复制以下模板反馈：

```text
【Phase 23 手工测试反馈】

环境：
OS：
Python：
Node：
npm：

Frontend:
npm test：PASS / FAIL
npm run build：PASS / FAIL

Backend:
pytest -q：PASS / FAIL

RBAC:
HTTP RBAC：PASS / FAIL
Owner Scope：PASS / FAIL
Admin Scope：PASS / FAIL
Filter：PASS / FAIL
Pagination：PASS / FAIL
Audit Scope：PASS / FAIL

失败信息：
<粘贴首个失败用例完整输出>

Git 状态：
<git status --short 输出>
```

## 9. 结果处理规则

- 全部 PASS：进入 Phase 23 最终验收。
- 任一 FAIL：记录失败原因，开发修复后重新执行对应测试。
- 环境问题：记录环境、命令和完整错误，不判定代码通过。
- CI 仍保持暂停，直到手工验证结果稳定后再单独安排 CI 恢复任务。
