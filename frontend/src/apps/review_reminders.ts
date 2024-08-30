import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import ReviewReminders from "@/components/ReviewReminders.vue";

createApp(ReviewReminders).mount("#review-reminders");
