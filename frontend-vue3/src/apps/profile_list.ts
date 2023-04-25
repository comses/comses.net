import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import ProfileListSidebar from "@/components/ProfileListSidebar.vue";
import { extractDataParams } from "./util";

const props = extractDataParams("sidebar", ["userId"]);
createApp(ProfileListSidebar, props).mount("#sidebar");
