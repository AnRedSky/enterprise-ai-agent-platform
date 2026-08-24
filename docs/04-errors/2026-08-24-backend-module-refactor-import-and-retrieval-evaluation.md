# 2026-08-24 Backend 模块重构测试残留：旧入口与评估模块循环依赖

## 1. 现象

本地重构验收继续执行时发现：

1. `tests/unit/test_observability.py` 仍引用已删除的 `app.services.observability_service`；
2. Retrieval Evaluation 的数据集、baseline、config 测试仍引用已删除的根级模块；
3. `app/services/retrieval_evaluation/dataset.py` 从包入口导入 `RetrievalEvaluationCase`，而包入口同时导入 dataset，形成循环导入；
4. `test_tool_runtime_failures.py` 在 SQLite 内存库执行 `Base.metadata.create_all` 时，因 `Execution` 引用了 `model_profiles`，但测试未显式加载 `ModelProfile` ORM 映射而出现 `NoReferencedTableError`。

## 2. 根因

本轮领域迁移已经删除旧 Service 入口，但测试 import 没有完全跟随物理迁移；Retrieval Evaluation 子模块内部依赖反向指向包聚合入口；独立 SQLite 测试依赖 ORM 元数据注册顺序，而测试只导入了部分模型模块。

## 3. 修复原则

- 测试直接使用 canonical domain package 或明确的子模块入口，不恢复兼容垫片；
- Retrieval Evaluation 子模块只从 `.service` 获取领域 Case，包 `__init__.py` 负责聚合公开入口，避免反向依赖；
- SQLite 测试显式导入所需模型模块，使 `model_profiles`、`model_providers`、`organizations` 等外键目标进入同一 `Base.metadata`；
- 不新增第二套 Service、Repository、Provider 或旧路径转发实现；
- 新增/重构模块继续补充中文职责、边界和关键依赖说明。

## 4. 验证状态

本次修复基于本地反馈进行代码整改；当前环境未执行仓库本地命令，因此不能记录本次修复后的测试为通过。后续必须由开发者在本地执行 Module Refactor Gate 与 Backend Regression，并以实际输出更新阶段文档。
