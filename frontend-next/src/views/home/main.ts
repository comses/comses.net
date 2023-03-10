import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import HelloWorld from "@/views/home/HelloWorld.vue";

createApp(HelloWorld).mount("#app");
