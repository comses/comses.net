import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import CodebaseEditForm from "@/components/CodebaseEditForm.vue";
import { extractIdFromPath } from "@/util";

const props = { codebaseId: extractIdFromPath(window.location.pathname, "codebases") };
console.log(props.codebaseId);
createApp(CodebaseEditForm, props).mount("#codebase-form");
