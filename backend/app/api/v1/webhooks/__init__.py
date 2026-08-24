"""Webhook API 领域包。

职责：承接外部 Webhook 请求并转换为 Trigger Service 调用。
边界：不实现签名校验、幂等和执行创建规则；这些职责统一由 WebhookTriggerService 负责。
关键依赖：FastAPI、WebhookTriggerService 与数据库依赖。
"""
