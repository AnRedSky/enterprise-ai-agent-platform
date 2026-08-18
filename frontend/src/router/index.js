import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../api/auth";
import Dashboard from "../views/Dashboard.vue";
import Agents from "../views/Agents.vue";
import Runtime from "../views/Runtime.vue";
import AuditLog from "../views/AuditLog.vue";
import Login from "../views/Login.vue";
const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: "/login", component: Login, meta: { public: true } },
        { path: "/", redirect: "/dashboard" },
        { path: "/dashboard", component: Dashboard },
        { path: "/agents", component: Agents },
        { path: "/runtime", component: Runtime },
        { path: "/runtime/audit", component: AuditLog }
    ]
});
router.beforeEach((to) => {
    if (to.meta.public)
        return true;
    if (!isAuthenticated())
        return { path: "/login", query: { redirect: to.fullPath } };
    return true;
});
export default router;
