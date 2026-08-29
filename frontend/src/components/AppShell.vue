<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearSession, getRoles, getUserId } from "@/api/auth";
import {
  Bell,
  Box,
  Document,
  Expand,
  Fold,
  FolderOpened,
  Grid,
  HelpFilled,
  House,
  Lightning,
  MoreFilled,
  OfficeBuilding,
  UserFilled,
} from "@element-plus/icons-vue";
import {
  ElAside,
  ElAvatar,
  ElBreadcrumb,
  ElBreadcrumbItem,
  ElButton,
  ElContainer,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElHeader,
  ElIcon,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElScrollbar,
  ElSubMenu,
  ElTag,
} from "element-plus";

const route = useRoute();
const router = useRouter();
const collapsed = ref(localStorage.getItem("enterprise_agent_sidebar_collapsed") === "1");
const navigation = [
  { path: "/dashboard", label: "工作台", icon: House },
  { path: "/agents", label: "Agent 管理", icon: Box },
  { path: "/tools", label: "Tool 管理", icon: Grid },
  { path: "/knowledge", label: "知识库", icon: FolderOpened },
  {
    path: "/workflows",
    label: "工作流",
    icon: Lightning,
    children: [
      { path: "/workflows", label: "工作流编排" },
      { path: "/workflows/triggers", label: "触发器" },
    ],
  },
  { path: "/organizations", label: "组织管理", icon: OfficeBuilding },
  { path: "/runtime", label: "运行记录", icon: Box },
  { path: "/runtime/audit", label: "审计日志", icon: Document },
];
const titleMap: Record<string, string> = {
  "/dashboard": "工作台",
  "/agents": "Agent 管理",
  "/tools": "Tool 管理",
  "/knowledge": "知识库",
  "/workflows": "工作流编排",
  "/workflows/triggers": "触发器",
  "/organizations": "组织管理",
  "/runtime": "运行记录",
  "/runtime/audit": "审计日志",
};
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
const expandedMenus = computed(() => {
  if (route.path.startsWith("/workflows")) return ["/workflows"];
  return [];
});

function navigate(path: string) {
  void router.push(path);
}

function toggleSidebar() {
  collapsed.value = !collapsed.value;
  localStorage.setItem("enterprise_agent_sidebar_collapsed", collapsed.value ? "1" : "0");
}

function logout() {
  clearSession();
  void router.replace({ path: "/login", query: { redirect: route.fullPath } });
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside :width="collapsed ? '72px' : '248px'" class="app-sidebar">
      <button class="brand" type="button" aria-label="返回工作台" @click="navigate('/dashboard')">
        <div class="brand-mark"><el-icon :size="21"><Grid /></el-icon></div>
        <div v-if="!collapsed" class="brand-copy"><strong>Enterprise AI</strong><span>Agent Platform</span></div>
      </button>

      <el-scrollbar class="nav-scroll">
        <div v-if="!collapsed" class="nav-section-title">平台</div>
        <el-menu
          :default-active="activeMenu"
          :default-openeds="expandedMenus"
          :collapse="collapsed"
          class="app-menu"
        >
          <template v-for="item in navigation" :key="item.path">
            <el-sub-menu v-if="item.children" :index="item.path">
              <template #title>
                <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
              </template>
              <el-menu-item v-for="child in item.children" :key="child.path" :index="child.path" @click="navigate(child.path)">
                {{ child.label }}
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="item.path" @click="navigate(item.path)">
              <el-icon><component :is="item.icon" /></el-icon><template #title>{{ item.label }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div v-if="!collapsed" class="sidebar-footer">
        <div class="support-card">
          <el-icon><HelpFilled /></el-icon>
          <div><strong>需要帮助？</strong><span>查看平台操作指南</span></div>
          <el-icon><MoreFilled /></el-icon>
        </div>
        <div class="system-status"><i></i><span>平台服务正常</span><small>v0.1</small></div>
      </div>
    </el-aside>

    <el-container class="content-container">
      <el-header class="app-header">
        <div class="header-left">
          <el-button text class="collapse-button" :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'" @click="toggleSidebar">
            <el-icon :size="19"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item>企业 AI 平台</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-actions">
          <el-button text circle aria-label="帮助"><el-icon><HelpFilled /></el-icon></el-button>
          <el-button text circle aria-label="通知"><el-icon><Bell /></el-icon></el-button>
          <el-tag size="small" effect="plain" class="env-tag">本地环境</el-tag>
          <el-dropdown trigger="click">
            <button class="user-menu" type="button">
              <el-avatar :size="34"><el-icon><UserFilled /></el-icon></el-avatar>
              <span class="user-meta"><strong>{{ userLabel }}</strong><small>{{ roleLabel }}</small></span>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="navigate('/organizations')">组织管理</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main">
        <div class="page-frame">
          <router-view v-slot="{ Component }">
            <transition name="page" mode="out-in"><component :is="Component" /></transition>
          </router-view>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell { min-height: 100vh; background: #f5f7fa; }
.app-sidebar { display: flex; flex-direction: column; border-right: 1px solid #e4e7ed; background: #fff; transition: width .2s ease; }
.brand { width: 100%; min-height: 68px; padding: 0 18px; display: flex; align-items: center; gap: 11px; border: 0; border-bottom: 1px solid #f0f2f5; background: #fff; color: #101828; cursor: pointer; text-align: left; }
.brand:hover { background: #fafafa; }
.brand-mark { width: 34px; height: 34px; flex: 0 0 34px; display: grid; place-items: center; border-radius: 9px; background: #111827; color: #fff; }
.brand-copy { display: grid; gap: 1px; min-width: 0; }
.brand-copy strong { font-size: 14px; line-height: 1.2; white-space: nowrap; }
.brand-copy span { color: #98a2b3; font-size: 10px; letter-spacing: .04em; white-space: nowrap; }
.nav-scroll { flex: 1; padding: 12px 10px; }
.nav-section-title { padding: 4px 12px 8px; color: #98a2b3; font-size: 11px; font-weight: 700; letter-spacing: .06em; }
.app-menu { border-right: 0; background: transparent; }
.app-menu :deep(.el-menu-item), .app-menu :deep(.el-sub-menu__title) { height: 42px; line-height: 42px; margin: 2px 0; border-radius: 7px; color: #475467; }
.app-menu :deep(.el-menu-item:hover), .app-menu :deep(.el-sub-menu__title:hover) { background: #f2f4f7; color: #1d2939; }
.app-menu :deep(.el-menu-item.is-active) { background: #eef4ff; color: #2563eb; font-weight: 600; }
.app-menu :deep(.el-sub-menu .el-menu-item) { min-width: 0; padding-left: 48px !important; }
.sidebar-footer { padding: 12px; border-top: 1px solid #f0f2f5; }
.support-card { display: flex; align-items: center; gap: 9px; padding: 11px; border: 1px solid #eaecf0; border-radius: 9px; background: #fcfcfd; color: #667085; }
.support-card > div { flex: 1; display: grid; gap: 2px; min-width: 0; }
.support-card strong { color: #344054; font-size: 12px; }
.support-card span { color: #98a2b3; font-size: 10px; white-space: nowrap; }
.system-status { display: flex; align-items: center; gap: 7px; padding: 12px 4px 2px; color: #667085; font-size: 11px; }
.system-status i { width: 7px; height: 7px; border-radius: 50%; background: #67c23a; }
.system-status small { margin-left: auto; color: #98a2b3; }
.content-container { min-width: 0; }
.app-header { height: 68px; display: flex; align-items: center; justify-content: space-between; padding: 0 28px; border-bottom: 1px solid #e4e7ed; background: rgba(255,255,255,.96); }
.header-left, .header-actions { display: flex; align-items: center; gap: 8px; }
.collapse-button { width: 36px; height: 36px; color: #667085; }
.breadcrumb { margin-left: 4px; }
.env-tag { margin-left: 8px; }
.user-menu { display: flex; align-items: center; gap: 9px; margin-left: 6px; padding: 2px 0 2px 6px; border: 0; background: transparent; cursor: pointer; }
.user-meta { display: grid; gap: 2px; text-align: left; }
.user-meta strong { color: #344054; font-size: 12px; line-height: 1.2; }
.user-meta small { color: #98a2b3; font-size: 10px; line-height: 1.2; }
.app-main { padding: 0; overflow: auto; }
.page-frame { min-height: calc(100vh - 68px); }
:deep(.page-enter-active), :deep(.page-leave-active) { transition: opacity .12s ease, transform .12s ease; }
:deep(.page-enter-from) { opacity: 0; transform: translateY(3px); }
:deep(.page-leave-to) { opacity: 0; }
@media (max-width: 700px) {
  .app-sidebar { width: 72px !important; }
  .brand { justify-content: center; padding: 0; }
  .nav-scroll { padding-inline: 8px; }
  .app-header { padding: 0 14px; }
  .breadcrumb { display: none; }
  .header-actions > .el-button { display: none; }
  .env-tag { display: none; }
  .user-meta { display: none; }
}
</style>
