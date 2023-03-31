import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import FormDemo from "@/components/FormDemo.vue";

createApp(FormDemo).mount("#app");
