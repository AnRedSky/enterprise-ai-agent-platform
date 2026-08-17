# 04 - Phase 1.3 Tool Runtime 开发记录

## 1. 上一阶段

Phase 1.3 已完成 Model Provider Contract、Model Gateway、Mock Provider、OpenAI-compatible Provider 与流式模型调用基础能力，并建立项目架构、开发和提交规范。

## 2. 本阶段目标

实现安全、可治理的 Tool Runtime 第一版：

- Tool Registry 与 AgentTool 权限关联
- Tool 参数 Schema 校验
- HTTP Tool 执行器
- 请求超时与响应大小限制
- SSRF 基础防护
- Tool 调用次数限制
- Tool 调用审计
- Runtime 与 Tool Executor 解耦

## 3. 架构

```text
Agent Runtime
    |
    v
Tool Registry
    |
    v
Permission Check
    |
    v
Input Schema Validation
    |
    v
HTTP Tool Executor
    |
    +--> Timeout
    +--> URL Safety / SSRF Guard
    +--> Response Size Limit
    |
    v
Tool Result
    |
    v
AuditLog
```

## 4. 安全原则

1. 禁止任意 Python、Shell、系统命令执行。
2. HTTP Tool 默认只允许安全的 HTTP/HTTPS 请求。
3. 阻断 localhost、loopback、link-local、私有网络和 metadata endpoint 等目标。
4. 对 hostname 做 DNS 解析后的 IP 再进行网络范围检查，避免简单字符串过滤被绕过。
5. 每次 Tool 执行必须有超时和响应体上限。
6. Tool 必须经过 AgentTool 关联和启用状态检查。
7. 参数必须先通过 Tool Schema 校验，再执行。
8. Tool 执行产生审计记录。

## 5. API / 数据边界

Tool Registry 负责工具定义与 Agent 绑定；Tool Runtime 负责执行，不允许 API 层直接发起任意外部请求。

## 6. 测试要求

至少覆盖：

- 合法 HTTP URL
- localhost 拒绝
- 私网 IP 拒绝
- metadata endpoint 拒绝
- schema 参数错误
- timeout
- response size limit
- 未绑定 Agent 的 Tool 拒绝
- disabled Tool 拒绝
- Tool execution audit

## 7. 本阶段验收

完成代码、测试、开发文档后才能进入 Memory 阶段。

## 8. 下一步

完成 Tool Runtime 后进入 `05-phase-1.3-memory.md`，实现 Session Context 与基础长期 Memory。
