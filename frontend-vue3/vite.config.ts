import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const { resolve } = require("path");
const resolvePath = (relativePath: string) => {
  return resolve(__dirname, relativePath);
};

export default defineConfig({
  plugins: [vue()],
  root: resolvePath("./src"),
  base:
    process.env.NODE_ENV === "development"
      ? "http://localhost:5000/static/bundles/"
      : "/static/bundles/",
  server: {
    host: "0.0.0.0",
    port: 5000,
    origin: "http://localhost:5000",
    watch: {
      usePolling: true,
      disableGlobbing: false,
    },
  },
  resolve: {
    extensions: [".js", ".ts", ".scss", ".vue"],
    alias: {
      "@": resolvePath("./src"),
      "~": resolvePath("./node_modules"),
    },
  },
  build: {
    outDir: "/shared/vite/bundles",
    manifest: true,
    rollupOptions: {
      input: {
        main: resolvePath("./src/apps/main.ts"),
        metrics: resolvePath("./src/apps/metrics.ts"),
        codebase_list: resolvePath("./src/apps/codebase_list.ts"),
        codebase_edit: resolvePath("./src/apps/codebase_edit.ts"),
        codebase_download: resolvePath("./src/apps/codebase_download.ts"),
        event_list: resolvePath("./src/apps/event_list.ts"),
        event_edit: resolvePath("./src/apps/event_edit.ts"),
        job_list: resolvePath("./src/apps/job_list.ts"),
        job_edit: resolvePath("./src/apps/job_edit.ts"),
        profile_list: resolvePath("./src/apps/profile_list.ts"),
        profile_edit: resolvePath("./src/apps/profile_edit.ts"),
        // add more entry points here
      },
    },
  },
});
