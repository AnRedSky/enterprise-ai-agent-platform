# Frontend Phase 2.9 状态与交付边界

## 1. 当前基线

- Remote branch：`main`
- 当前前端基线：`7705da63`
- 前端技术栈：Vue 3 + TypeScript + Vite + Vitest
- Frontend Gate：`npm test` → `npm run build`

开发准则要求前端 API Types / UI 必须建立在已经稳定并完成后端验证的 Contract 之上；Runtime Integration 也必须等基础 API Contract 稳定且 Real API 可验收后再进入。当前阶段继续直接实现 2.9-D Webhook UI 会违反该顺序。

## 2. 最新后端状态

当前项目仍处于 Phase 2.9：

```text
2.9-A Event Contract              已完成
        ↓
2.9-B Durable Event Persistence   第一切片完成 + Migration 本地验收
        ↓
2.9-C Reliable Delivery           第一切片完成 / 第二切片开发中
        ↓
2.9-D Webhook Integration         尚未进入
        ↓
2.9-E Runtime Integration         尚未进入
```

2.9-C 第二切片正在准备真实 PostgreSQL 并发验收，目标包含多 Worker 原子 Claim、租约恢复、旧租约 fencing、retry/dead-letter、tenant isolation 和幂等投递。当前后端明确尚未声明这一 Real/并发验收完成，因此前端不能提前假设 Webhook Delivery API、endpoint 配置、签名、回放和 delivery audit 的最终 HTTP Contract。

## 3. 本次前端优化

### 3.1 增加 Frontend Gate npm 统一入口

新增：

```powershell
npm run test:gate
```

该入口只调用现有 Frontend Release Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\test\\release\\01_frontend_regression_gate.ps1
```

Gate 严格执行：

1. `npm test`
2. `npm run build`

不调用 Backend pytest、Alembic、Real API 或 Browser E2E，保持项目规定的 Gate 隔离。

### 3.2 为什么现在不提前实现 2.9-D

2.9-D 的正式目标是把已有 Webhook Trigger 能力接入 Durable Event Delivery，并统一 endpoint、签名、事件版本、幂等、回放和 delivery audit。上述业务 Contract 依赖 2.9-C 真实并发验收结果。

如果当前直接创建 frontend Webhook Delivery API/UI，会产生两类风险：

- 前端先于后端 Contract 固化，形成临时 API 类型和页面逻辑；
- 后续后端 Contract 调整时需要产生反向兼容代码，违反“唯一业务契约”和“禁止平行实现”的治理要求。

因此本次只完成一个实际可交付的前端工程优化：把现有且已验证的 Frontend Gate 暴露成统一 npm 入口，同时明确 2.9-D 的进入条件。不是用文档代替功能开发，也没有伪造尚未存在的后端 API。

## 4. 本地验收

开发者已经反馈本次基线：

```text
npm test
Test Files  19 passed (19)
Tests       87 passed (87)
```

并且：

```text
npm run build
✓ built in 6.00s
```

这两个结果属于开发者实际反馈，可以记录为当前基线验收结果。

修改 `package.json` 后，必须重新执行：

```powershell
cd frontend
npm run test:gate
```

然后再进行 Browser / Backend-Frontend 联调（如果后续任务范围需要）。本次代码提交后，不能把未重新执行的结果写成新的“通过”。

## 5. 2.9-D 前端进入条件

只有同时满足以下条件，才开始 Webhook Integration 前端 API Types/UI：

1. 2.9-C 第二切片真实 PostgreSQL 并发验收通过；
2. Backend HTTP Contract 明确并冻结；
3. endpoint / signing / event version / idempotency / replay / delivery audit 字段与错误语义明确；
4. Backend 对应 Unit/Integration/API Contract/Real API Gate 完成；
5. 再按固定顺序进入 Frontend API Types → Vitest → UI → Real API → Frontend Gate → Browser E2E。

## 6. 提交边界

本次变更属于同一个 Frontend Release Gate 开发者体验优化：`package.json` 的 npm 入口与本文件的设计记录必须一次原子提交，不拆分中间提交。
