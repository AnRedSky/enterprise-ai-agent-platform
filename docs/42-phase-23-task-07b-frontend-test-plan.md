# Phase 23 / Task 07-B：Frontend Test 验证计划

## 1. 上一阶段

Task 07-A 已完成第三方 TypeScript 声明检查问题修复，并提交 `8afe568e738b7caee0f1d450c76e0715efd088ea`。

## 2. 本阶段目标

在开发人员本地确认 Frontend Build 后，继续完成 Frontend 自动化测试验证。

## 3. 手工执行步骤

### Step 1：Build

```bash
cd frontend
npm run build
```

期望：命令退出码为 `0`，Vite 输出构建成功。

### Step 2：Unit / Component Test

```bash
npm test
```

期望：Vitest 全部测试通过，退出码为 `0`。

### Step 3：反馈格式

```text
npm run build：PASS / FAIL
npm test：PASS / FAIL

如果 FAIL：
- 第一处错误
- 完整错误堆栈
- Node.js 版本
- npm 版本
```

## 4. 失败处理原则

- 只修复实际失败项；
- 不修改测试使其“适配失败”；
- 不删除测试；
- 不使用 `any`、`@ts-ignore` 等方式隐藏业务类型错误；
- 第三方声明问题与业务源码问题分开处理；
- 每次修复后重新执行对应测试。

## 5. 下一阶段

Frontend Build + Test 全部 PASS 后，继续执行 Backend：

```bash
cd backend
pytest -q
pytest -q tests/test_runtime_http_rbac.py
pytest -q tests/test_runtime_rbac_matrix.py
```

Backend 验证完成后再决定 Phase 23 是否达到最终验收条件。
