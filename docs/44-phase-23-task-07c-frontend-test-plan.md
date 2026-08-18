# Phase 23 / Task 07-C：Frontend Test 验证规划

## 1. 上一阶段

Task 07-B 已修复 `Agents.vue` 的 Element Plus `DefaultRow` 与 `Agent` 类型不兼容问题。当前必须由开发人员本地执行 Build 验证。

## 2. 当前任务

### Step 1：Frontend Build

```bash
cd frontend
npm run build
```

期望：退出码 `0`，不出现 TypeScript 错误。

### Step 2：Frontend Unit / Component Test

Build 通过后执行：

```bash
npm test
```

期望：Vitest 全部测试通过，退出码 `0`。

### Step 3：Backend 测试

Frontend Build + Test 均通过后执行：

```bash
cd ../backend
pytest -q
pytest -q tests/test_runtime_http_rbac.py
pytest -q tests/test_runtime_rbac_matrix.py
```

## 3. 反馈格式

```text
npm run build：PASS / FAIL
npm test：PASS / FAIL
pytest -q：PASS / FAIL
HTTP RBAC：PASS / FAIL
RBAC Matrix：PASS / FAIL
```

失败时提供第一处失败以及完整错误输出。

## 4. 质量原则

- 不删除测试；
- 不通过 `any`、`@ts-ignore` 隐藏业务错误；
- 不把未执行结果标记为 PASS；
- 每次修复后重新执行对应验证；
- Phase 23 只有在 Frontend、Backend、HTTP RBAC 全部获得实际验证结果后才进行最终验收。

## 5. 后续任务

Task 07-C 完成后，根据实际测试结果修复剩余问题；全部通过后记录 Phase 23 完成，并进入下一阶段功能验收与 CI 恢复评估。
