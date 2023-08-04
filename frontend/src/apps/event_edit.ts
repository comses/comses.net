import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import EventEditForm from "@/components/EventEditForm.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("event-form", ["eventId"]);
createApp(EventEditForm, props).mount("#event-form");
