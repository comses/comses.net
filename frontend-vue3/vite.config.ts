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
        formdemo: resolvePath("./src/apps/formdemo.ts"),
        codebase_list: resolvePath("./src/apps/codebase_list.ts"),
        event_edit: resolvePath("./src/apps/event_edit.ts"),
        // add more entry points here
      },
    },
  },
});
