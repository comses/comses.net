import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import JobEditForm from "@/components/JobEditForm.vue";
import { extractIdFromPath } from "@/util";

const jobId = extractIdFromPath(window.location.pathname, "jobs");
const props = { jobId: jobId ? parseInt(jobId) : undefined };
createApp(JobEditForm, props).mount("#job-form");
