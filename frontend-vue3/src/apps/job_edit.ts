import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import JobEditForm from "@/components/JobEditForm.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("job-form", ["jobId"]);
createApp(JobEditForm, props).mount("#job-form");
