import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../api/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      component: () => import("../views/login/index.vue"),
      meta: { public: true },
    },
    { path: "/", redirect: "/dashboard" },
    { path: "/dashboard", component: () => import("../views/dashboard/index.vue") },
    { path: "/organizations", component: () => import("../views/organizations/index.vue") },
    { path: "/organizations/:id", component: () => import("../views/organizations/detail.vue") },
    { path: "/agents", component: () => import("../views/agents/index.vue") },
    { path: "/tools", component: () => import("../views/tools/index.vue") },
    { path: "/knowledge", component: () => import("../views/knowledge/index.vue") },
    { path: "/workflows", component: () => import("../views/workflows/index.vue") },
    { path: "/workflows/triggers", component: () => import("../views/workflow-triggers/index.vue") },
    { path: "/runtime", component: () => import("../views/runtime/index.vue") },
    {
      path: "/runtime/audit",
      component: () => import("../views/audit-log/index.vue"),
    },
  ],
});

router.beforeEach((to) => {
  if (to.meta.public) return true;
  if (!isAuthenticated()) return { path: "/login", query: { redirect: to.fullPath } };
  return true;
});

export default router;
