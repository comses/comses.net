import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import ReleaseDownloadFormModal from "@/components/ReleaseDownloadFormModal.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("download-form", ["userData", "versionNumber", "identifier"]);
createApp(ReleaseDownloadFormModal, props).mount("#download-form");
