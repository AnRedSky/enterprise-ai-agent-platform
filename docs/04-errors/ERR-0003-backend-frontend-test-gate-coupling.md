# ERR-0003 — Backend / Frontend Test Gate 跨栈耦合

- Legacy ID: `002-backend-frontend-test-gate-coupling`
- Phase: 1.5
- 类型: Test Governance

## 现象
旧 Full Regression Gate 同时调用 Backend pytest、Migration、Real API 与 Frontend npm test/build。

## 根因
把 release 全量回归误设计成单脚本，而不是独立质量 Gate。

## 修复
拆为 Backend regression gate、Frontend regression gate；Browser/E2E 独立为第三层。Backend 不调用 npm，Frontend 不调用 uv/pytest/Alembic/Real API。

## 验证
静态检查脚本边界，并分别从 backend/frontend 执行各自 Gate；未执行不得标记通过。
