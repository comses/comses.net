import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import ProfileEditForm from "@/components/ProfileEditForm.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("profile-form", ["userId", "connectionsUrl"]);
createApp(ProfileEditForm, props).mount("#profile-form");
