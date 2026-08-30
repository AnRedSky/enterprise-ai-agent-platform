# Agent Debug Experience 重复模块记录

## 1. 发现

2026-08-30 基于远端 `main` 审阅前端 Agent 模块时发现：

- `frontend/src/views/agents/components/AgentDebugExperience.vue`
- `frontend/src/views/agents/components/AgentDebugExperienceP11.vue`

两个文件具有完全相同的 Git Blob SHA：`46bda958c7bf48b67fccd698df517eda8a88b8b0`。

## 2. 根因

P1.1 迭代过程中曾以 `P11` 后缀保留临时/阶段性入口，但正式 `AgentDebugExperience.vue` 已成为唯一实际导入入口。继续保留完全相同的文件会形成重复模块，违反领域模块唯一正式实现与禁止平行能力的治理规则。

## 3. 修复

删除 `AgentDebugExperienceP11.vue`，保留 `AgentDebugExperience.vue` 作为唯一正式实现。

`frontend/src/views/agents/index.vue` 当前只导入正式文件，因此删除不会改变运行时入口。

## 4. 防回归

后续 Agent 调试能力必须扩展正式 `AgentDebugExperience.vue` 或其明确职责子模块，不再通过阶段后缀复制组件。
