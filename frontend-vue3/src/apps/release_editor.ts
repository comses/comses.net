import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "@/components/releaseEditor/App.vue";
import MetadataFormPage from "@/components/releaseEditor/MetadataFormPage.vue";
import UploadFormPage from "@/components/releaseEditor/UploadFormPage.vue";
import ContributorsPage from "@/components/releaseEditor/ContributorsPage.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("release-editor", [
  "versionNumber",
  "identifier",
  "reviewStatus",
  "isLive",
]);
console.log(props.reviewStatus);

const app = createApp(App, props);
const pinia = createPinia();

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    // only include upload route when release is unpublished
    { path: "/", redirect: { name: props.isLive ? "metadata" : "upload" } },
    ...(props.isLive ? [] : [{ path: "/upload", component: UploadFormPage, name: "upload" }]),
    { path: "/metadata", component: MetadataFormPage, name: "metadata" },
    { path: "/contributors", component: ContributorsPage, name: "contributors" },
  ],
});

app.use(pinia);
app.use(router);
app.mount("#release-editor");
