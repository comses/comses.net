import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import EventEditForm from "@/components/EventEditForm.vue";
import { extractIdFromPath } from "./util";

const props = { eventId: extractIdFromPath(window.location.pathname, "events") };
createApp(EventEditForm, props).mount("#event-form");
