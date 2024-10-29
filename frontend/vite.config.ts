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
      input: {
        main: resolvePath("./src/apps/main.ts"),
        codebase_list: resolvePath("./src/apps/codebase_list.ts"),
        codebase_edit: resolvePath("./src/apps/codebase_edit.ts"),
        event_calendar: resolvePath("./src/apps/event_calendar.ts"),
        event_list: resolvePath("./src/apps/event_list.ts"),
        event_edit: resolvePath("./src/apps/event_edit.ts"),
        image_gallery: resolvePath("./src/apps/image_gallery.ts"),
        job_list: resolvePath("./src/apps/job_list.ts"),
        job_edit: resolvePath("./src/apps/job_edit.ts"),
        metrics: resolvePath("./src/apps/metrics.ts"),
        profile_list: resolvePath("./src/apps/profile_list.ts"),
        profile_edit: resolvePath("./src/apps/profile_edit.ts"),
        release_editor: resolvePath("./src/apps/release_editor.ts"),
        release_download: resolvePath("./src/apps/release_download.ts"),
        release_regenerate_share_uuid: resolvePath("./src/apps/release_regenerate_share_uuid.ts"),
        review_editor: resolvePath("./src/apps/review_editor.ts"),
        review_reminders: resolvePath("./src/apps/review_reminders.ts"),
        reviewer_list: resolvePath("./src/apps/reviewer_list.ts"),
      },
    },
  },
});
