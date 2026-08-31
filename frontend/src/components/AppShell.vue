<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearSession, getRoles, getUserId } from "@/api/auth";
import { Bell, Box, Connection, Document, Expand, Fold, FolderOpened, Grid, HelpFilled, House, Lightning, OfficeBuilding, Search, UserFilled, DataAnalysis } from "@element-plus/icons-vue";
import { ElAvatar, ElBreadcrumb, ElBreadcrumbItem, ElButton, ElContainer, ElDropdown, ElDropdownItem, ElDropdownMenu, ElHeader, ElIcon, ElMain, ElMenu, ElMenuItem, ElScrollbar, ElTag } from "element-plus";

const route = useRoute();
const router = useRouter();
const collapsed = ref(localStorage.getItem("enterprise_agent_sidebar_collapsed") === "1");
const navigation = [
  { section: "工作台", items: [{ path: "/dashboard", label: "总览", icon: House, description: "平台运行概况" }] },
  { section: "AI 资产", items: [
    { path: "/agents", label: "智能体", icon: Box, description: "创建、版本与发布" },
    { path: "/tools", label: "工具", icon: Grid, description: "工具能力与启用状态" },
    { path: "/knowledge", label: "知识库", icon: FolderOpened, description: "知识资产与检索" },
  ] },
  { section: "自动化", items: [
    { path: "/workflows", label: "工作流", icon: Lightning, description: "编排与执行" },
    { path: "/workflows/triggers", label: "触发器", icon: Bell, description: "调度与事件触发" },
  ] },
  { section: "运行与治理", items: [
    { path: "/runtime", label: "运行中心", icon: Box, description: "Execution、Event 与 Trace" },
    { path: "/runtime/operations", label: "运行运维", icon: DataAnalysis, description: "事件、投递、SLO 与死信" },
    { path: "/runtime/audit", label: "审计日志", icon: Document, description: "治理操作与执行审计" },
  ] },
  { section: "平台管理", items: [
    { path: "/organizations", label: "组织与成员", icon: OfficeBuilding, description: "Tenant、成员与模型配置" },
    { path: "/integrations", label: "集成中心", icon: Connection, description: "Webhook 与事件出站" },
  ] },
];
const titleMap: Record<string, string> = { "/dashboard": "总览", "/agents": "智能体", "/tools": "工具", "/knowledge": "知识库", "/workflows": "工作流编排", "/workflows/triggers": "触发器", "/organizations": "组织与成员", "/runtime": "运行中心", "/runtime/operations": "运行运维", "/runtime/audit": "审计日志", "/integrations": "集成中心" };
const currentTitle = computed(() => {
  if (route.path.startsWith("/organizations/") && route.path.endsWith("/model-providers")) return "模型 Provider";
  if (route.path.startsWith("/organizations/")) return "组织详情";
  return titleMap[route.path] || "企业 AI 平台";
});
const userLabel = computed(() => getUserId() || "当前用户");
const roleLabel = computed(() => getRoles()[0] || "成员");
const activeMenu = computed(() => {
  if (route.path.startsWith("/organizations/")) return "/organizations";
  if (route.path.startsWith("/workflows/triggers")) return "/workflows/triggers";
  return route.path;
});
const expandedMenus = computed(() => route.path.startsWith("/workflows") ? ["/workflows"] : []);
function navigate(path: string) { void router.push(path); }
function toggleSidebar() { collapsed.value = !collapsed.value; localStorage.setItem("enterprise_agent_sidebar_collapsed", collapsed.value ? "1" : "0"); }
function logout() { clearSession(); void router.replace({ path: "/login", query: { redirect: route.fullPath } }); }
</script>

<template>
  <el-container class="app-shell">
    <el-aside :width="collapsed ? '72px' : '256px'" class="app-sidebar">
      <button class="brand" type="button" aria-label="返回工作台" @click="navigate('/dashboard')">
        <div class="brand-mark"><el-icon :size="20"><Grid /></el-icon></div>
        <div v-if="!collapsed" class="brand-copy"><strong>Enterprise AI</strong><span>Agent Platform</span></div>
      </button>
      <button v-if="!collapsed" class="workspace-switcher" type="button" aria-label="切换工作区">
        <span class="workspace-icon"><el-icon><OfficeBuilding /></el-icon></span>
        <span class="workspace-copy"><small>当前工作区</small><strong>企业默认空间</strong></span>
        <el-icon class="workspace-chevron"><Expand /></el-icon>
      </button>
      <el-scrollbar class="nav-scroll">
        <template v-for="group in navigation" :key="group.section">
          <div v-if="!collapsed" class="nav-section-title">{{ group.section }}</div>
          <el-menu :default-active="activeMenu" :default-openeds="expandedMenus" :collapse="collapsed" class="app-menu">
            <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path" :title="collapsed ? item.label : item.description" @click="navigate(item.path)">
              <el-icon><component :is="item.icon" /></el-icon><template #title><span class="menu-label">{{ item.label }}</span></template>
            </el-menu-item>
          </el-menu>
        </template>
      </el-scrollbar>
      <div v-if="!collapsed" class="sidebar-footer"><div class="system-status"><i></i><span>平台服务正常</span><small>v0.1</small></div></div>
    </el-aside>
    <el-container class="content-container">
      <el-header class="app-header">
        <div class="header-left">
          <el-button text class="collapse-button" :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'" @click="toggleSidebar"><el-icon :size="19"><Fold v-if="!collapsed" /><Expand v-else /></el-icon></el-button>
          <el-breadcrumb separator="/" class="breadcrumb"><el-breadcrumb-item>企业 AI 平台</el-breadcrumb-item><el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item></el-breadcrumb>
        </div>
        <div class="header-actions">
          <el-button text class="search-button" aria-label="全局搜索"><el-icon><Search /></el-icon><span>搜索</span><kbd>⌘ K</kbd></el-button>
          <el-button text circle aria-label="帮助"><el-icon><HelpFilled /></el-icon></el-button>
          <el-button text circle aria-label="通知"><el-icon><Bell /></el-icon></el-button>
          <el-tag size="small" effect="plain" class="env-tag">本地环境</el-tag>
          <el-dropdown trigger="click"><button class="user-menu" type="button"><el-avatar :size="34"><el-icon><UserFilled /></el-icon></el-avatar><span class="user-meta"><strong>{{ userLabel }}</strong><small>{{ roleLabel }}</small></span></button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="navigate('/organizations')">组织与成员</el-dropdown-item><el-dropdown-item @click="navigate('/integrations')">集成中心</el-dropdown-item><el-dropdown-item divided @click="logout">退出登录</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main"><div class="page-frame"><router-view v-slot="{ Component }"><transition name="page" mode="out-in"><component :is="Component" /></transition></router-view></div></el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell { min-height: 100vh; background: var(--ui-bg-page); }
.app-sidebar { display: flex; flex-direction: column; border-right: 1px solid var(--ui-border-default); background: var(--ui-bg-surface); transition: width .2s ease; }
.brand { width: 100%; min-height: var(--ui-header-height); padding: 0 18px; display: flex; align-items: center; gap: 11px; border: 0; border-bottom: 1px solid var(--ui-color-gray-100); background: var(--ui-bg-surface); color: var(--ui-text-primary); cursor: pointer; text-align: left; }
.brand:hover { background: var(--ui-bg-subtle); }
.brand-mark { width: 34px; height: 34px; flex: 0 0 34px; display: grid; place-items: center; border-radius: var(--ui-radius-sm); background: var(--ui-text-primary); color: #fff; }
.brand-copy { display: grid; gap: 1px; }
.brand-copy strong { font-size: 14px; line-height: 18px; white-space: nowrap; }
.brand-copy span { color: var(--ui-text-placeholder); font-size: 10px; letter-spacing: .04em; }
.workspace-switcher { width: calc(100% - 24px); margin: 12px; padding: 9px; border: 1px solid var(--ui-border-default); border-radius: var(--ui-radius-md); display: flex; align-items: center; gap: 9px; background: var(--ui-bg-subtle); color: var(--ui-text-primary); cursor: pointer; text-align: left; }
.workspace-switcher:hover { border-color: var(--ui-border-strong); background: #fff; }
.workspace-icon { width: 30px; height: 30px; display: grid; place-items: center; flex: 0 0 30px; border-radius: var(--ui-radius-xs); background: var(--ui-color-brand-50); color: var(--ui-color-brand-600); }
.workspace-copy { min-width: 0; display: grid; gap: 2px; }
.workspace-copy small { color: var(--ui-text-placeholder); font-size: 9px; }
.workspace-copy strong { overflow: hidden; color: var(--ui-color-gray-700); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.workspace-chevron { margin-left: auto; color: var(--ui-text-placeholder); transform: rotate(45deg); }
.nav-scroll { flex: 1; padding: 6px 10px; }
.nav-section-title { padding: 12px 12px 5px; color: var(--ui-text-placeholder); font-size: 10px; font-weight: 700; letter-spacing: .08em; }
.app-menu { border-right: 0; background: transparent; }
.app-menu :deep(.el-menu-item) { height: 40px; margin: 2px 0; border-radius: var(--ui-radius-sm); color: var(--ui-text-secondary); }
.app-menu :deep(.el-menu-item:hover) { background: var(--ui-color-gray-100); color: var(--ui-text-primary); }
.app-menu :deep(.el-menu-item.is-active) { background: var(--ui-color-brand-50); color: var(--ui-color-brand-600); font-weight: 600; }
.app-menu :deep(.el-icon) { margin-right: 10px; }
.sidebar-footer { padding: 12px; border-top: 1px solid var(--ui-color-gray-100); }
.system-status { display: flex; align-items: center; gap: 7px; padding: 5px 4px; color: var(--ui-text-tertiary); font-size: 11px; }
.system-status i { width: 7px; height: 7px; border-radius: 50%; background: var(--ui-color-success-600); box-shadow: 0 0 0 3px rgba(3,152,85,.1); }
.system-status small { margin-left: auto; color: var(--ui-text-placeholder); }
.content-container { min-width: 0; }
.app-header { height: var(--ui-header-height); display: flex; align-items: center; justify-content: space-between; padding: 0 28px; border-bottom: 1px solid var(--ui-border-default); background: rgba(255,255,255,.94); backdrop-filter: blur(12px); }
.header-left, .header-actions { display: flex; align-items: center; gap: 8px; }
.collapse-button { width: 36px; height: 36px; color: var(--ui-text-secondary); }
.breadcrumb { margin-left: 4px; }
.header-actions { gap: 4px; }
.search-button { height: 34px; margin-right: 4px; padding: 0 9px; color: var(--ui-text-tertiary); gap: 7px; }
.search-button kbd { padding: 2px 5px; border: 1px solid var(--ui-border-strong); border-radius: 4px; background: var(--ui-bg-subtle); color: var(--ui-text-placeholder); font-size: 9px; }
.env-tag { margin: 0 6px; }
.user-menu { display: flex; align-items: center; gap: 9px; margin-left: 4px; padding: 3px 5px; border: 0; border-radius: var(--ui-radius-sm); background: transparent; cursor: pointer; }
.user-menu:hover { background: var(--ui-color-gray-100); }
.user-meta { display: grid; gap: 2px; text-align: left; }
.user-meta strong { max-width: 120px; overflow: hidden; color: var(--ui-color-gray-700); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.user-meta small { color: var(--ui-text-placeholder); font-size: 10px; }
.app-main { padding: 0; overflow: auto; background: var(--ui-bg-page); }
.page-frame { min-height: 100%; }
:deep(.page-enter-active), :deep(.page-leave-active) { transition: opacity .12s ease, transform .12s ease; }
:deep(.page-enter-from) { opacity: 0; transform: translateY(3px); }
:deep(.page-leave-to) { opacity: 0; }
@media (max-width: 900px) { .search-button span, .search-button kbd { display: none; } }
@media (max-width: 700px) {
  .app-sidebar { width: var(--ui-sidebar-collapsed) !important; }
  .brand { justify-content: center; padding: 0; }
  .nav-scroll { padding-inline: 8px; }
  .app-header { padding: 0 14px; }
  .breadcrumb, .env-tag, .user-meta, .header-actions > .el-button { display: none; }
  .search-button { display: none; }
}
</style>
