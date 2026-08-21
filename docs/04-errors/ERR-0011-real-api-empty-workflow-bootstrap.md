# ERR-0011 — Real API bootstrap 选择空 Workflow Definition

- Legacy ID: `007-real-api-bootstrap-empty-workflow-definition`
- Phase: 1.5-F

Real API 创建 Execution 返回 422：Workflow definition 必须有非空 `nodes`。bootstrap 曾创建 `{nodes: [], edges: []}` 或复用空 definition 的 published Workflow。修复为 `input -> output` 最小可执行 fixture，并在复用 published version 前检查 definition 可执行性；无可用 fixture 时自动创建有效版本。修复后要求重新 Real API Gate。
