# LT-04 API / Developer Platform

## 1. 目标
把现有业务 API 提升为可供企业内部开发者和外部系统稳定集成的 Developer Platform。

## 2. 当前状态
**待立项。** 当前已有 FastAPI API Contract 和 Real API 验收体系，但完整 Developer Platform 能力尚未完成。

## 3. 主要缺口
- API 生命周期与版本策略；
- OpenAPI/文档门户；
- API Key/OAuth/Service Account 等调用身份；
- Webhook subscription 与事件消费；
- SDK/客户端生成与版本管理；
- rate limit、quota、tenant isolation；
- API usage/cost analytics；
- deprecation/compatibility policy；
- 开发者审计与凭证管理。

## 4. 长期拆解
API inventory → Contract/versioning → Developer identity → Credential governance → Rate limit/quota → SDK/Webhook → Usage portal → E2E 验收。

## 5. 完成判定
核心 API 具备稳定版本、认证、限流、配额、文档、SDK/事件集成和兼容策略，并有真实调用验收。
