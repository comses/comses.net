import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import CodebaseEditForm from "@/components/CodebaseEditForm.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("codebase-form", ["codebaseId"]);
createApp(CodebaseEditForm, props).mount("#codebase-form");
