# Phase 2.6 — Resume Failure-after-Resume Acceptance

> 状态：**验收入口已实现，待开发者本地实际执行**。
> 本文不预填测试通过结果；真实 PostgreSQL、真实 HTTP、独立 Worker 的结果以开发者本地执行反馈为准。

## 1. 目的

在已有 `Source failed → Checkpoint → Resume pending → Worker → 剩余 Node 成功` 验收之外，验证 Resume 本身再次失败时不会破坏 Durable Resume 的 lineage 与终态边界。

本验收覆盖：

```text
Source failed
   ↓
Source Checkpoint persisted
   ↓
Resume Execution created
   ↓
Independent Worker claim
   ↓
Resume Runtime fails
   ↓
Resume remains failed
```

## 2. 必须满足的不变量

1. Source Execution 始终保持 `failed`。
2. Source Execution 不会被 Resume 创建或执行过程改写为 `pending` / `running`。
3. Resume Execution 的 `resume_of_execution_id` 必须固定指向 Source。
4. Resume Execution 的 `workflow_version_id` 必须与 Source 相同。
5. Resume Execution 的 `resume_checkpoint_sequence` 必须固定指向 Source 的恢复 Checkpoint。
6. Resume 只重新执行 Checkpoint 之后的 Node；Source 已完成 Node 不得复制到 Resume Node Execution。
7. Resume 失败的 Node 不得追加 `node.completed` Checkpoint。
8. Resume 失败后不得出现伪造的 `completed` Execution 或成功 Checkpoint。
9. Source / Resume 的 Checkpoint sequence 独立编号，不能跨 Execution 混用。
10. Worker ownership 在终态后必须清理，不得遗留活动 lease。

## 3. 自动化入口

在 API Service 与独立 Worker 已由开发者手工启动的前提下：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\04_run_durable_resume_failure_acceptance.ps1
```

脚本只负责：

- 检查 Real API source baseline；
- 检查 API / Worker 是否已经运行；
- 准备 tenant-safe Real API context；
- 执行 `tests/api_real/test_workflow_resume_failure_api.py`。

脚本**不会**启动、停止或重启 API、Scheduler、Worker。

## 4. 测试场景

测试使用真实 PostgreSQL 持久化 Workflow Execution，并构造：

```text
prepare(input)
    ↓
broken-agent(agent)
```

`prepare` 成功并产生 Checkpoint；`broken-agent` 使用不存在的 Agent ID，确保 Source 首次执行失败。

随后通过正式 `WorkflowExecutionService.resume_from_latest_checkpoint()` 创建新的 pending Resume Execution，由独立 Worker 消费。

Resume 从 `prepare` Checkpoint 之后开始，因此只会执行 `broken-agent`，并再次失败。

## 5. 本地验证顺序

先确认 API / Worker 已使用本次代码重新启动，再执行：

```powershell
cd backend
uv run pytest -q
```

然后执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\03_run_durable_resume_acceptance.ps1
```

再执行 failure-after-resume：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\04_run_durable_resume_failure_acceptance.ps1
```

其中直接执行：

```powershell
uv run pytest -q tests/api_real/test_workflow_resume_failure_api.py
```

如果没有 `ACCESS_TOKEN` / `ORGANIZATION_ID` 等 Real API Context，或者未显式启用 `real_api` marker，不能作为 Real API Gate 通过依据；应使用上述正式 PowerShell Gate。

## 6. 结果记录要求

只有开发者实际执行后，才允许在 `docs/PROJECT_STATUS.md`、Phase 文档或错误记录中写入具体通过数量、耗时及最终验收结论。

若测试暴露新的工程错误，必须按照 `docs/01-governance/DEVELOPMENT.md` 将已完成分析的错误记录到 `docs/04-errors/`，并形成独立修复提交。
