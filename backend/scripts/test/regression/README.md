# Regression

阶段性总回归入口只负责编排已经存在的测试入口，不复制测试实现。

`01_backend_regression.ps1` 用于 Backend 全量 pytest 回归。

后续 Phase 验证脚本应迁移到本目录或其子目录，并按测试用途命名；禁止继续在 `backend/scripts` 根目录新增 `run_phase_*`。
