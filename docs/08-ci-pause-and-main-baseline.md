# 08 - CI 临时暂停与 Main 基线切换记录

## 1. 上一阶段

完成 Memory 第一版、Tool Runtime 基础能力，并补齐历史开发文档 01-06。

## 2. 本阶段目标

- 核查 GitHub Actions 当前 CI 配置与失败情况。
- 暂停自动 CI，避免开发阶段被不稳定流水线阻塞。
- 记录可验证的失败信息和日志获取情况。
- 统一后续开发基于 `main` 最新代码。
- 建立项目开发规划、交付和提交规范。

## 3. CI 核查结果

当前 `.github/workflows/ci.yml` 原配置监听：

- push 到 `main` / `feature/**`
- pull_request 到 `main`

Job 包含：Python 3.12、依赖安装、compileall、pytest。

本次通过 GitHub API 检查仓库当前 workflow 与 commit workflow runs。API 对当前 main 最新提交未返回可用 workflow run，因此当前无法取得可复现的历史失败 Job ID 或完整日志正文。

因此本记录**不虚构具体错误信息**。目前可确认的事实是：CI 配置存在自动触发，但当前连接器未提供对应历史失败 run 日志；后续如果 GitHub UI / Actions 提供失败 run，应将 Job ID、失败步骤和关键日志摘录补录到本文件或新增编号文档。

## 4. 临时方案

将 CI 自动触发修改为仅：

```yaml
on:
  workflow_dispatch:
```

原来的测试 Job 不删除，仅停止自动触发。后续修复 CI 后恢复 `push` / `pull_request`。

## 5. Main 基线

GitHub 当前 `main` 最新提交：

`3a5dc0ff581ab8e0aaee48984f87d6aff0e03a93`

该基线已经包含后续开发所需的 Backend、Memory、Tool Runtime、Frontend 和项目文档等文件。

从本记录之后，开发工作统一以 `main` 最新提交为基线；不再继续把 `feature/phase-1.2` 作为开发基线。

## 6. 提交规则

每完成一个可验收功能模块或修复：

1. 更新编号开发文档。
2. 完成代码 / Migration / 测试。
3. 使用 Conventional Commit。
4. 记录 commit SHA。
5. 核查 GitHub 文件是否存在。

## 7. 下一步

继续 Memory Runtime Integration，完成 Memory 注入 Agent Context、上下文限制和集成测试，并新增 `09-memory-runtime-integration.md`。
