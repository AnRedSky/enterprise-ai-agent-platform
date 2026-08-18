import { createRouter, createWebHistory } from "vue-router";
import Dashboard from "../views/Dashboard.vue";
import Agents from "../views/Agents.vue";
import Runtime from "../views/Runtime.vue";
import AuditLog from "../views/AuditLog.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/dashboard" },
    { path: "/dashboard", component: Dashboard },
    { path: "/agents", component: Agents },
    { path: "/runtime", component: Runtime },
    { path: "/runtime/audit", component: AuditLog }
  ]
});
