import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import fs from "fs";

const { resolve } = require("path");
const resolvePath = (relativePath: string) => {
  return resolve(__dirname, relativePath);
};

const getAppEntries = () => {
  const appsDir = resolvePath("./src/apps");
  const entries: { [key: string]: string } = {};

  fs.readdirSync(appsDir).forEach(file => {
    if (file.endsWith(".ts")) {
      const name = file.replace(".ts", "");
      entries[name] = resolvePath(`./src/apps/${file}`);
    }
  });

  return entries;
};

export default defineConfig({
  plugins: [vue()],
  root: resolvePath("./src"),
  base:
    process.env.NODE_ENV === "development"
      ? "http://localhost:5173/static/bundles/"
      : "/static/bundles/",
  server: {
    host: "0.0.0.0",
    port: 5173,
    origin: "http://localhost:5173",
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
      external: [/holder\.js.*/],
      input: getAppEntries(),
    },
  },
  /*
  optimizeDeps: {
    exclude: [],
  }
  */
});
