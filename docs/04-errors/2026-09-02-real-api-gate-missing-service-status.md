# Real API Gate 缺少受保护服务时的状态语义错误

## 1. 现象

开发者执行 Backend Regression Gate 时，Backend Regression 与 Alembic head 验证均通过，但 Scheduler 未运行，Real API Gate 直接抛出异常并被 Release Gate 报告为 `Tenant-safe real API validation failed`。

## 2. 根因

项目开发准则明确规定：Real API Gate 可以探测 API / Worker / Scheduler 等受保护服务，但禁止自动创建、启动、重启或停止服务；依赖服务缺失时必须明确输出“未执行”，不能把环境前置条件缺失伪装成测试失败。

原实现使用 PowerShell `throw` 表示服务缺失，导致“未执行”被上层 Release Gate 当成“测试失败”。这混淆了测试结果与环境前置条件状态。

## 3. 修复

- Real API Gate 对 API、Worker、Scheduler 分别执行只读状态探测；
- 缺少任一受保护服务时输出 `[NOT RUN]`；
- 使用退出码 `2` 表示“前置条件缺失、测试未执行”；
- Release Gate 将退出码 `2` 转换为 `[NOT RUN]`，不报告为测试失败；
- 非零且非 `2` 的退出码仍保持真实测试失败语义；
- Gate 全程不创建、启动、重启或停止任何受保护服务；
- 测试上下文仍由 Gate 自动生成，不要求开发者手工填写 Token、ID 或 fixture 数据。

## 4. 验证要求

服务齐全时，Real API Gate 必须继续执行完整 tenant-safe Real API 测试；测试失败仍必须阻断 Release Gate。

服务缺失时，Backend Unit 与 migration 可以完成，Real API 标记为 `NOT RUN`，Release Gate 退出码为 `2`，并明确给出标准人工启动命令。
