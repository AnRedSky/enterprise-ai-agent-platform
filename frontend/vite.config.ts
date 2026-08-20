import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBaseUrl = env.VITE_API_BASE_URL || "http://localhost:8000";

  return {
    plugins: [vue()],
    resolve: {
      alias: { "@": "/src" },
    },
    server: {
      host: env.VITE_DEV_HOST || "127.0.0.1",
      port: Number(env.VITE_DEV_PORT || 5173),
      proxy: {
        "/api": apiBaseUrl,
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes("node_modules")) return undefined;
            if (id.includes("@vueuse")) return "vueuse-vendor";
            if (id.includes("element-plus")) return "element-plus-vendor";
            if (id.includes("@element-plus/icons-vue")) return "element-plus-icons";
            if (id.includes("vue-router")) return "vue-router-vendor";
            if (id.includes("pinia")) return "pinia-vendor";
            if (id.includes("axios")) return "axios-vendor";
            if (id.includes("/vue/")) return "vue-vendor";
            return undefined;
          },
        },
        onwarn(warning, defaultHandler) {
          // @vueuse/core 14.3.x shipped two misplaced PURE annotations.
          // Rollup removes these annotations safely, so filter only this
          // known upstream INVALID_ANNOTATION warning rather than hiding all
          // build diagnostics. The project can remove this filter after the
          // dependency is upgraded to a fixed release.
          if (
            warning.code === "INVALID_ANNOTATION" &&
            warning.message.includes("@vueuse/core")
          ) {
            return;
          }
          defaultHandler(warning);
        },
      },
    },
  };
});
