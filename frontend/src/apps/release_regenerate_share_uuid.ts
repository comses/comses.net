import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import ReleaseRegenerateShareUUID from "@/components/ReleaseRegenerateShareUUID.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("regenerate-share-uuid", [
  "initialShareUrl",
  "versionNumber",
  "identifier",
]);
createApp(ReleaseRegenerateShareUUID, props).mount("#regenerate-share-uuid");
