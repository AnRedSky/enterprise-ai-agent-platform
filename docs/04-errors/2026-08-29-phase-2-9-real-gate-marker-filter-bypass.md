# Phase 2.9-C Real Gate 被 pytest 默认 marker 过滤

## 1. 现象

开发者本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.9\01_reliable_delivery_postgres_gate.ps1
```

Migration/head 检查成功，但 PostgreSQL 真实验收阶段输出：

```text
5 deselected in 0.05s
Phase 2.9-C PostgreSQL Real Gate failed.
```

## 2. 根因

`backend/pyproject.toml` 的 pytest 默认配置包含：

```toml
addopts = "-m 'not real_api' --import-mode=importlib"
```

Phase 2.9-C 的真实 PostgreSQL 测试文件整体使用 `pytest.mark.real_api` 标记。该专用 Gate 原先只传入测试文件路径，没有显式覆盖 `-m` 过滤条件，因此继承默认 `not real_api`，导致真实验收测试全部被 deselect。

这不是 PostgreSQL、Migration 或 Durable Delivery 业务实现失败，而是测试 Gate 的 marker 选择与全局 pytest 默认配置不一致。

## 3. 修复

将 Phase 2.9-C Real Gate 的真实验收命令改为：

```powershell
uv run pytest -q tests/api_real/test_integration_event_delivery_postgres.py --tb=short -m real_api
```

通过显式 `-m real_api` 覆盖默认 marker 过滤，使该 Gate 真正执行五个 PostgreSQL 并发/恢复/隔离验收测试。

## 4. 影响范围

- 不修改生产业务代码；
- 不修改全局 pytest 默认策略，避免 Backend default regression 自动执行真实外部依赖测试；
- 仅修正 Phase 2.9-C 专用 Real Gate 的测试选择逻辑；
- Gate 继续不自动启动或停止 API、Worker、Scheduler、Redis、PostgreSQL；
- 测试数据继续由真实验收测试自动生成和清理。

## 5. 验证要求

修复提交后必须由开发者在本地真实 PostgreSQL 环境重新执行 Phase 2.9-C Gate。只有看到五个真实验收测试实际执行并通过，才能将 2.9-C 第二切片标记为 Real Gate 已验收。
