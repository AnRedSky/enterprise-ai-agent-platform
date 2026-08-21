# ERR-0013 — Backend / Frontend Test Gate 违反隔离原则

- Legacy ID: `009-test-gate-backend-frontend-coupling`

旧 `01_full_regression_gate.ps1` 同时执行 pytest、migration、Real API、npm test/build，违反 Gate 独立原则。修复为 Backend regression gate + Frontend regression gate，Browser/E2E 第三层；删除旧 Full Regression 编排。验证要求是分别执行并检查命令边界，未执行不得标记通过。
