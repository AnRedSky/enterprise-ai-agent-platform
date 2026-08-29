<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearSession, getRoles, getUserId } from "@/api/auth";
import { Bell, Box, Connection, Document, Expand, Fold, FolderOpened, Grid, HelpFilled, House, Lightning, OfficeBuilding, UserFilled } from "@element-plus/icons-vue";
import { ElAside, ElAvatar, ElBreadcrumb, ElBreadcrumbItem, ElButton, ElContainer, ElDropdown, ElDropdownItem, ElDropdownMenu, ElHeader, ElIcon, ElMain, ElMenu, ElMenuItem, ElScrollbar, ElSubMenu, ElTag } from "element-plus";

const route = useRoute();
const router = useRouter();
const collapsed = ref(localStorage.getItem("enterprise_agent_sidebar_collapsed") === "1");
const navigation = [
  { section: "工作台", items: [{ path: "/dashboard", label: "总览", icon: House }] },
  { section: "AI 资产", items: [
    { path: "/agents", label: "智能体", icon: Box },
    { path: "/tools", label: "工具", icon: Grid },
    { path: "/knowledge", label: "知识库", icon: FolderOpened },
  ] },
  { section: "自动化", items: [{ path: "/workflows", label: "工作流", icon: Lightning }, { path: "/workflows/triggers", label: "触发器", icon: Bell }] },
  { section: "运行与治理", items: [{ path: "/runtime", label: "运行中心", icon: Box }, { path: "/runtime/audit", label: "审计日志", icon: Document }] },
  { section: "平台管理", items: [{ path: "/organizations", label: "组织与成员", icon: OfficeBuilding }, { path: "/integrations", label: "集成中心", icon: Connection }] },
];
const titleMap: Record<string, string> = {
  "/dashboard": "总览", "/agents": "智能体", "/tools": "工具", "/knowledge": "知识库", "/workflows": "工作流编排", "/workflows/triggers": "触发器", "/organizations": "组织与成员", "/runtime": "运行中心", "/runtime/audit": "审计日志", "/integrations": "集成中心",
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
const expandedMenus = computed(() => route.path.startsWith("/workflows") ? ["/workflows"] : []);
function navigate(path: string) { void router.push(path); }
function toggleSidebar() { collapsed.value = !collapsed.value; localStorage.setItem("enterprise_agent_sidebar_collapsed", collapsed.value ? "1" : "0"); }
function logout() { clearSession(); void router.replace({ path: "/login", query: { redirect: route.fullPath } }); }
</script>

<template>
  <el-container class="app-shell">
    <el-aside :width="collapsed ? '72px' : '248px'" class="app-sidebar">
      <button class="brand" type="button" aria-label="返回工作台" @click="navigate('/dashboard')">
        <div class="brand-mark"><el-icon :size="21"><Grid /></el-icon></div>
        <div v-if="!collapsed" class="brand-copy"><strong>Enterprise AI</strong><span>Agent Platform</span></div>
      </button>
      <el-scrollbar class="nav-scroll">
        <template v-for="group in navigation" :key="group.section">
          <div v-if="!collapsed" class="nav-section-title">{{ group.section }}</div>
          <el-menu :default-active="activeMenu" :default-openeds="expandedMenus" :collapse="collapsed" class="app-menu">
            <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path" @click="navigate(item.path)">
              <el-icon><component :is="item.icon" /></el-icon><template #title>{{ item.label }}</template>
            </el-menu-item>
          </el-menu>
        </template>
      </el-scrollbar>
      <div v-if="!collapsed" class="sidebar-footer">
        <div class="system-status"><i></i><span>平台服务正常</span><small>v0.1</small></div>
      </div>
    </el-aside>
    <el-container class="content-container">
      <el-header class="app-header">
        <div class="header-left">
          <el-button text class="collapse-button" :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'" @click="toggleSidebar"><el-icon :size="19"><Fold v-if="!collapsed" /><Expand v-else /></el-icon></el-button>
          <el-breadcrumb separator="/" class="breadcrumb"><el-breadcrumb-item>企业 AI 平台</el-breadcrumb-item><el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item></el-breadcrumb>
        </div>
        <div class="header-actions">
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
.app-shell{min-height:100vh;background:#f5f7fa}.app-sidebar{display:flex;flex-direction:column;border-right:1px solid #e4e7ed;background:#fff;transition:width .2s ease}.brand{width:100%;min-height:68px;padding:0 18px;display:flex;align-items:center;gap:11px;border:0;border-bottom:1px solid #f0f2f5;background:#fff;color:#101828;cursor:pointer;text-align:left}.brand:hover{background:#fafafa}.brand-mark{width:34px;height:34px;flex:0 0 34px;display:grid;place-items:center;border-radius:9px;background:#111827;color:#fff}.brand-copy{display:grid;gap:1px}.brand-copy strong{font-size:14px;line-height:1.2;white-space:nowrap}.brand-copy span{color:#98a2b3;font-size:10px;letter-spacing:.04em}.nav-scroll{flex:1;padding:10px}.nav-section-title{padding:8px 12px 5px;color:#98a2b3;font-size:10px;font-weight:700;letter-spacing:.08em}.app-menu{border-right:0;background:transparent}.app-menu :deep(.el-menu-item){height:40px;line-height:40px;margin:2px 0;border-radius:7px;color:#475467}.app-menu :deep(.el-menu-item:hover){background:#f2f4f7;color:#1d2939}.app-menu :deep(.el-menu-item.is-active){background:#eef4ff;color:#2563eb;font-weight:600}.sidebar-footer{padding:12px;border-top:1px solid #f0f2f5}.system-status{display:flex;align-items:center;gap:7px;padding:6px 4px;color:#667085;font-size:11px}.system-status i{width:7px;height:7px;border-radius:50%;background:#67c23a}.system-status small{margin-left:auto;color:#98a2b3}.content-container{min-width:0}.app-header{height:68px;display:flex;align-items:center;justify-content:space-between;padding:0 28px;border-bottom:1px solid #e4e7ed;background:rgba(255,255,255,.96)}.header-left,.header-actions{display:flex;align-items:center;gap:8px}.collapse-button{width:36px;height:36px;color:#667085}.breadcrumb{margin-left:4px}.env-tag{margin-left:8px}.user-menu{display:flex;align-items:center;gap:9px;margin-left:6px;padding:2px 0 2px 6px;border:0;background:transparent;cursor:pointer}.user-meta{display:grid;gap:2px;text-align:left}.user-meta strong{color:#344054;font-size:12px}.user-meta small{color:#98a2b3;font-size:10px}.app-main{padding:0;overflow:auto}.page-frame{min-height:calc(100vh - 68px)}:deep(.page-enter-active),:deep(.page-leave-active){transition:opacity .12s ease,transform .12s ease}:deep(.page-enter-from){opacity:0;transform:translateY(3px)}:deep(.page-leave-to){opacity:0}@media(max-width:700px){.app-sidebar{width:72px!important}.brand{justify-content:center;padding:0}.nav-scroll{padding-inline:8px}.app-header{padding:0 14px}.breadcrumb{display:none}.header-actions>.el-button,.env-tag,.user-meta{display:none}}
</style>
