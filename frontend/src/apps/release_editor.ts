import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "@/components/releaseEditor/App.vue";
import MetadataFormPage from "@/components/releaseEditor/MetadataFormPage.vue";
import UploadFormPage from "@/components/releaseEditor/UploadFormPage.vue";
import ImportedArchivePage from "@/components/releaseEditor/ImportedArchivePage.vue";
import ContributorsPage from "@/components/releaseEditor/ContributorsPage.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("release-editor", [
  "versionNumber",
  "identifier",
  "reviewStatus",
  "isLive",
  "canEditOriginals",
  "isImported",
]);

// check if ?publish or ?upload-image is in the url, set prop, and clear from the url
const urlParams = new URLSearchParams(window.location.search);
props.showPublishModal = urlParams.has("publish");
props.showUploadImageModal = urlParams.has("upload-image");
window.history.replaceState({}, "", window.location.pathname + window.location.hash);

const app = createApp(App, props);
const pinia = createPinia();

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    // only include upload route when original files are editable
    {
      path: "/",
      redirect: {
        name: props.isImported ? "package" : props.canEditOriginals ? "upload" : "metadata",
      },
    },
    ...(props.canEditOriginals && !props.isImported
      ? [{ path: "/upload", component: UploadFormPage, name: "upload" }]
      : []),
    // use the imported archive page for imported releases
    ...(props.isImported
      ? [{ path: "/package", component: ImportedArchivePage, name: "package" }]
      : []),
    { path: "/metadata", component: MetadataFormPage, name: "metadata" },
    { path: "/contributors", component: ContributorsPage, name: "contributors" },
  ],
});

app.use(pinia);
app.use(router);
app.mount("#release-editor");
