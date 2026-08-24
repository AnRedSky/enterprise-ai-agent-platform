# ERR-0025：Backend Refactor Closure Gate 将 canonical Service 包入口误判为旧 import

## 1. 现象

执行 `backend/scripts/test/module-refactor/05_backend_refactor_closure_gate.ps1` 时，Gate 将以下实际 canonical Service 包入口报告为 legacy import：

```text
app.services.organization
app.services.session_service
app.services.runtime_query
app.services.usage_accounting
app.services.retrieval_evaluation
```

同时还包括这些包被其他 canonical 模块正常依赖的情况。

## 2. 根因

旧 Service 实现文件已迁移为同名子模块包，例如：

```text
app/services/organization/__init__.py
app/services/organization/service.py
```

按照当前模块化规则，`app.services.organization` 本身就是正式入口，由 `__init__.py` 暴露 `OrganizationService`。Closure Gate 原先使用 `app\.services\.<legacy-module>` 的文本前缀扫描，无法区分“旧扁平文件 import”和“同名 canonical package import”，因此产生 false positive。

这与开发准则关于“子模块通过 `__init__.py` 暴露正式入口”的要求冲突。

## 3. 修复

调整 `05_backend_refactor_closure_gate.ps1`：

- 不再使用无法区分 package / legacy module 的 Service import 正则；
- Service 迁移状态改由旧扁平文件是否存在、`app/services` 根目录是否存在领域实现共同判断；
- API、Runtime、`app.tools.registry` 等具有明确旧路径边界的 import 继续执行全仓扫描；
- 保留 Provider 唯一实现入口、Runtime Governance 重复实现和中文模块职责说明检查。

## 4. 验证边界

本修复提交后需要由开发者本地重新执行 Closure Gate，并继续执行完整重构 Gate 链及 Backend Regression。

在开发者实际执行前，不将 Closure Gate 标记为通过。

## 5. 预防

后续静态 Gate 设计必须区分：

1. 已删除的旧文件路径；
2. 仍合法存在的 canonical package 路径；
3. 真正已经废弃的 import 路径。

禁止使用会把 canonical package 名称本身判定为 legacy 的宽泛正则。
