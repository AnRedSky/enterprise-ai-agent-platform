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
const collapsed = ref(false);
const navigation = [
  { path: "/dashboard", label: "工作台", icon: House },
  { path: "/agents", label: "Agent 管理", icon: Box },
  { path: "/tools", label: "Tool 管理", icon: Grid },
  { path: "/knowledge", label: "知识库", icon: FolderOpened },
  {
    path: "/workflows",
    label: "工作流",
    icon: Lightning,
    children: [{ path: "/workflows", label: "工作流编排" }, { path: "/workflows/triggers", label: "触发器" }],
  },
  { path: "/organizations", label: "组织管理", icon: OfficeBuilding },
  { path: "/runtime", label: "运行记录", icon: Box },
  { path: "/runtime/audit", label: "审计日志", icon: Document },
];
const titleMap: Record<string, string> = {
  "/dashboard": "工作台", "/agents": "Agent 管理", "/tools": "Tool 管理", "/knowledge": "知识库",
  "/workflows": "工作流编排", "/workflows/triggers": "触发器", "/organizations": "组织管理",
  "/runtime": "运行记录", "/runtime/audit": "审计日志",
};
const currentTitle = computed(() => {
  if (route.path.startsWith("/organizations/") && route.path.endsWith("/model-providers")) return "模型 Provider";
  if (route.path.startsWith("/organizations/")) return "组织详情";
  return titleMap[route.path] || "企业 AI 平台";
});
const userLabel = computed(() => getUserId() || "当前用户");
const roleLabel = computed(() => getRoles()[0] || "成员");
const activeMenu = computed(() => route.path);

function navigate(path: string) {
  void router.push(path);
}

function handleMenuSelect(index: string) {
  navigate(index);
}

function logout() {
  clearSession();
  void router.replace({ path: "/login", query: { redirect: route.fullPath } });
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside :width="collapsed ? '72px' : '248px'" class="app-sidebar">
      <div class="brand" @click="navigate('/dashboard')">
        <div class="brand-mark"><el-icon :size="22"><Grid /></el-icon></div>
        <div v-if="!collapsed" class="brand-copy"><strong>Enterprise AI</strong><span>Agent Platform</span></div>
      </div>
      <el-scrollbar class="nav-scroll">
        <el-menu :default-active="activeMenu" :collapse="collapsed" class="app-menu" @select="handleMenuSelect">
          <template v-for="item in navigation" :key="item.path">
            <el-sub-menu v-if="item.children" :index="item.path">
              <template #title><el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span></template>
              <el-menu-item v-for="child in item.children" :key="child.path" :index="child.path">{{ child.label }}</el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="item.path">
              <el-icon><component :is="item.icon" /></el-icon><template #title>{{ item.label }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>
      <div v-if="!collapsed" class="sidebar-footer">
        <div class="support-card"><el-icon><HelpFilled /></el-icon><div><strong>需要帮助？</strong><span>查看平台操作指南</span></div><el-icon><MoreFilled /></el-icon></div>
        <div class="system-status"><i></i><span>平台服务正常</span><small>v0.1</small></div>
      </div>
    </el-aside>
    <el-container class="content-container">
      <el-header class="app-header">
        <div class="header-left">
          <el-button text class="collapse-button" @click="collapsed = !collapsed"><el-icon :size="19"><Fold v-if="!collapsed" /><Expand v-else /></el-icon></el-button>
          <el-breadcrumb separator="/" class="breadcrumb"><el-breadcrumb-item>企业 AI 平台</el-breadcrumb-item><el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item></el-breadcrumb>
        </div>
        <div class="header-actions">
          <el-button text circle aria-label="帮助"><el-icon><HelpFilled /></el-icon></el-button>
          <el-button text circle aria-label="通知"><el-icon><Bell /></el-icon></el-button>
          <el-tag size="small" effect="plain" class="env-tag">本地环境</el-tag>
          <el-dropdown trigger="click">
            <button class="user-menu" type="button"><el-avatar :size="34"><el-icon><UserFilled /></el-icon></el-avatar><span class="user-meta"><strong>{{ userLabel }}</strong><small>{{ roleLabel }}</small></span></button>
            <template #dropdown><el-dropdown-menu><el-dropdown-item @click="navigate('/organizations')">组织管理</el-dropdown-item><el-dropdown-item divided @click="logout">退出登录</el-dropdown-item></el-dropdown-menu></template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main"><div class="page-frame"><router-view v-slot="{ Component }"><transition name="page" mode="out-in"><component :is="Component" /></transition></router-view></div></el-main>
    </el-container>
  </el-container>
</template>
