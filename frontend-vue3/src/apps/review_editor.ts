import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import ReviewEditor from "@/components/ReviewEditor.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("review-editor", ["reviewId", "statusLevels", "status"]);
createApp(ReviewEditor, props).mount("#review-editor");
