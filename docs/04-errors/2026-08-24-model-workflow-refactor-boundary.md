# 2026-08-24 Model / Workflow 模块边界整改错误记录

## 1. 问题

Model 领域完成物理迁移后，`app/runtime/agent_runtime.py` 仍引用已删除的 `app.runtime.model_gateway`；同时 Scheduler Recovery Slot 的公开调用契约在实例调用与类级调用之间发生回归，导致既有单元测试出现参数绑定错误。Scheduler Repository 时间参数测试还直接依赖 SQLAlchemy 自动生成的 bind 名称，出现 `KeyError: next_run_at`。

## 2. 根因

1. Model Runtime 迁移只完成了目标模块落位，调用方 import 全量切换没有作为同一交付单元结束。
2. Recovery Slot 从实例配置方法调整为其他调用形式时，没有同时保留已有实例调用与类级纯函数调用的契约。
3. Scheduler Repository 测试把 SQLAlchemy 编译器生成的内部 bind 名称当成业务契约，导致实现虽保持 UTC naive 转换，测试却因名称变化失败。

## 3. 修复原则

- Model Runtime 只通过 `app.runtime.model` 暴露 Gateway 与 ModelResult。
- Recovery Slot 只保留一套计算规则，同时兼容已有实例配置和显式类级参数调用。
- Scheduler 时间边界仍由 Repository 负责 UTC naive 归一化；测试验证语义，不绑定 ORM 编译器内部命名。
- Workflow 重构遵循“物理迁移、全量 import 切换、删除旧入口、无兼容垫片”的规则，不允许旧实现与新实现并存。

## 4. 当前状态

本记录对应的代码变更已直接提交 `main`。本环境未执行开发者本地 pytest 或 Module Refactor Gate，因此不在此预填通过结果；本地验证必须以实际执行输出为准。
