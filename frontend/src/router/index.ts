import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../api/auth";
import Dashboard from "../views/dashboard/index.vue";
import Agents from "../views/agents/index.vue";
import Runtime from "../views/runtime/index.vue";
import AuditLog from "../views/audit-log/index.vue";
import Tools from "../views/tools/index.vue";
import Knowledge from "../views/knowledge/index.vue";
import Login from "../views/login/index.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: Login, meta: { public: true } },
    { path: "/", redirect: "/dashboard" },
    { path: "/dashboard", component: Dashboard },
    { path: "/agents", component: Agents },
    { path: "/tools", component: Tools },
    { path: "/knowledge", component: Knowledge },
    { path: "/runtime", component: Runtime },
    { path: "/runtime/audit", component: AuditLog },
  ],
});

router.beforeEach((to) => {
  if (to.meta.public) return true;
  if (!isAuthenticated()) return { path: "/login", query: { redirect: to.fullPath } };
  return true;
});

export default router;
