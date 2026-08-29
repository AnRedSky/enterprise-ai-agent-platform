# LT-02 Enterprise IAM / SSO / Identity Federation

## 1. 目标
在现有 Tenant、Organization、RBAC 基础上形成企业级统一身份与访问体系，支持企业目录、SSO、身份联邦和生命周期治理。

## 2. 当前状态
**待立项。** 现有组织、租户、角色和权限治理已具备基础能力，但不等同于完整企业 IAM。

## 3. 主要缺口
- OIDC/SAML SSO；
- 企业 IdP / Directory Federation；
- 用户与组织生命周期同步；
- Group → Role 映射；
- SCIM 或等价生命周期接口；
- MFA/强认证策略对接边界；
- Service Account / Machine Identity；
- Session、token、凭证生命周期；
- 跨组织委派与最小权限模型。

## 4. 长期拆解
身份模型 → Federation Contract → 用户同步 → Group/RBAC 映射 → Service Identity → 生命周期与审计 → 安全验收。

## 5. 完成判定
企业 IdP 接入、身份生命周期、权限映射、服务身份、安全审计均有正式 Contract 和 Real API/安全验收；不得破坏既有 Tenant boundary。
