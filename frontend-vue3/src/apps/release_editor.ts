import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import ReleaseEditor from "@/components/ReleaseEditor.vue";
import ReleaseEditorMetadataForm from "@/components/ReleaseEditorMetadataForm.vue";
import ReleaseEditorUploadForm from "@/components/ReleaseEditorUploadForm.vue";
import ReleaseEditorContributors from "@/components/ReleaseEditorContributors.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("release-editor", [
  "versionNumber",
  "identifier",
  "reviewStatus",
  "isLive",
]);
console.log(props.reviewStatus);

const app = createApp(ReleaseEditor, props);
const pinia = createPinia();

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    // only include upload route when release is unpublished
    { path: "/", redirect: { name: props.isLive ? "metadata" : "upload" } },
    ...(props.isLive
      ? []
      : [{ path: "/upload", component: ReleaseEditorUploadForm, name: "upload" }]),
    { path: "/metadata", component: ReleaseEditorMetadataForm, name: "metadata" },
    { path: "/contributors", component: ReleaseEditorContributors, name: "contributors" },
  ],
});

app.use(pinia);
app.use(router);
app.mount("#release-editor");
