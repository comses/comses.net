import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import EventEditForm from "@/components/EventEditForm.vue";

// FIXME: this sort of thing is used alot, should have a util function extracting values from path
function getEventId(pathname: string) {
  const match = pathname.match(/\/events\/([0-9]+)\/edit\//);
  return match ? parseInt(match[1]) : undefined;
}

const eventId = getEventId(document.location.pathname);
createApp(EventEditForm, { eventId }).mount("#event-form");
