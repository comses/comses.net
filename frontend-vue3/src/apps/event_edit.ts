import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import EventEditForm from "@/components/EventEditForm.vue";
import { extractIdFromPath } from "@/util";

const eventId = extractIdFromPath(window.location.pathname, "events");
const props = { eventId: eventId ? parseInt(eventId) : undefined };
createApp(EventEditForm, props).mount("#event-form");
