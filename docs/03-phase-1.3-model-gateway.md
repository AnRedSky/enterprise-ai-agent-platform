# 03 - Phase 1.3 Model Gateway 开发记录

## 1. 上一阶段

Phase 1.2 建立了 Agent、Session/Message、SSE Runtime、基础 Tool Registry 与 Model Gateway 骨架。

## 2. 当前目标

将模型供应商差异从 Agent Runtime 中隔离，建立统一 Provider Contract，并支持 OpenAI-compatible 普通与流式调用。

## 3. 当前完成

- Model Provider Contract
- ModelResult / ModelUsage
- Model Gateway
- Mock Provider
- OpenAI-compatible Provider
- Streaming Provider
- Token Usage 基础字段
- Agent Runtime 与 Provider 解耦
- 超时与错误边界的 Provider 抽象

## 4. 架构

```text
Agent Runtime
      |
      v
Model Gateway
      |
      v
Provider Contract
   +--+----------------+
   |                   |
 Mock          OpenAI-compatible
```

Runtime 不直接依赖具体厂商 SDK 或 HTTP 实现。

## 5. 关键问题

Provider 类型定义曾可能造成 Gateway 与 OpenAI Provider 循环依赖，后续将公共契约独立为 provider 层，保持单向依赖。

## 6. 下一步

进入 Tool Runtime；Tool 完成后进入 Memory，Memory 以 Session Context 与基础长期记忆为第一目标。
