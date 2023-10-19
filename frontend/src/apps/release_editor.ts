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
  "canEditOriginals",
]);

// check if ?publish is in the url, set prop, and clear from the url
const urlParams = new URLSearchParams(window.location.search);
props.showPublishModal = urlParams.has("publish");
window.history.replaceState({}, "", window.location.pathname + window.location.hash);

const app = createApp(App, props);
const pinia = createPinia();

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    // only include upload route when original files are editable
    { path: "/", redirect: { name: props.canEditOriginals ? "upload" : "metadata" } },
    ...(props.canEditOriginals
      ? [{ path: "/upload", component: UploadFormPage, name: "upload" }]
      : []),
    { path: "/metadata", component: MetadataFormPage, name: "metadata" },
    { path: "/contributors", component: ContributorsPage, name: "contributors" },
  ],
});

app.use(pinia);
app.use(router);
app.mount("#release-editor");
