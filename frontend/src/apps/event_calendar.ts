import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import EventCalendar from "@/components/EventCalendar.vue";

createApp(EventCalendar).mount("#event-calendar");
