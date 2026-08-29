# LT-09 Agent Asset / Marketplace

## 1. 目标
建立 Agent、Workflow、Tool、Prompt、Knowledge 等 AI 资产的生命周期、版本、发布、审批、共享和复用体系。

## 2. 当前状态
**候选长期任务。** 当前已有 Agent/Version/Workflow 等资产基础，但尚未形成统一资产中心或 Marketplace。

## 3. 主要缺口
- Asset catalog；
- ownership 与 namespace；
- immutable version；
- publish/unpublish；
- approval/review；
- organization/private/public sharing；
- dependency/version compatibility；
- import/export；
- usage/rating；
- 安全扫描与治理。

## 4. 长期拆解
资产模型 → Ownership/namespace → Version/release → Review/approval → Sharing → Dependency governance → Catalog UI → Usage feedback。

## 5. 完成判定
资产可版本化、审批、发布、回滚、共享并追踪依赖和使用情况；跨组织共享具备明确授权与审计。

## 6. 前置约束
必须先明确资产所有权、版本不可变性、审批和跨组织共享边界，再进入正式 Phase。
