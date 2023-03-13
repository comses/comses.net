import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import HelloWorld from "@/components/HelloWorld.vue";

createApp(HelloWorld).mount("#app");
