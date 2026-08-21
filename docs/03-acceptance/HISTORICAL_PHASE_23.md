# Historical Phase 23 — Acceptance / Historical Evidence

> 历史验收记录，不作为当前项目状态源。

## 1. 历史验收过程

Phase 23 当时要求由开发者在本地执行 Frontend、Backend、HTTP RBAC 和 Build，并以实际命令输出决定 PASS/FAIL；`39-manual-test-execution-guide.md` 明确禁止以代码存在替代实际测试。

## 2. Frontend 历史反馈

Task 07-A 修复第三方 TypeScript declarations 后要求重新 build；Task 07-B 又修复 `Agents.vue` 的 `DefaultRow` / `Agent` 类型边界；Task 08 首次人工反馈为 6 个测试文件 5 failed / 1 passed、8 tests 4 failed / 4 passed，随后删除重复 JS 测试、补 `mount`、`vi.hoisted` 和 Element Plus/v-loading stubs。

Task 07-C 后续实际反馈：

```text
npm run build：PASS
npm test：PASS
```

因此 Frontend 验证在历史阶段最终形成实际通过证据。

## 3. Frontend 验收脚本

Task 09 新增 `frontend/scripts/run_manual_frontend_suite.ps1`，执行 test/build 并保留原始输出；backend manual suite 增加 frontend/all mode。脚本存在本身不等于用户环境测试通过。

## 4. Backend / RBAC 历史状态

Phase 23 原记录要求继续执行 `pytest -q`、HTTP Runtime RBAC 和 RBAC Matrix，并在全部关键测试通过前不恢复 CI。当前可确认的历史来源中没有完整、独立的 Phase 23 Backend Final Acceptance 文档，因此不虚构 Backend 最终通过数字。

## 5. 结论

Phase 23 是历史开发时间线，不能覆盖当前 Phase 1.2–1.8 的正式状态。当前项目状态只读取 `PROJECT_STATUS.md`。

## 6. 来源

`24`、`25`、`26`、`27`、`28`、`29`、`30`、`31`、`32`、`36`、`37`、`38`、`39`、`40`、`41`、`42`、`43`、`44`、`45` 对应旧 Phase 23 记录，具体文件迁移映射见 `DOCS_MIGRATION_MATRIX.md`。
