import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const { resolve } = require("path");

export default defineConfig({
  plugins: [vue()],
  root: resolve("./src"),
  base:
    process.env.NODE_ENV === "development"
      ? "http://localhost:3000/static/bundles/"
      : "/static/bundles/",
  server: {
    host: "0.0.0.0",
    port: 5000,
    watch: {
      usePolling: true,
      disableGlobbing: false,
    },
  },
  resolve: {
    extensions: [".js", ".ts", ".scss", ".vue"],
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    outDir: "/shared/vite/bundles",
    manifest: true,
    rollupOptions: {
      input: {
       home: resolve("./src/views/home/main.ts"),
        // add more pages here
      },
    },
  },
});
