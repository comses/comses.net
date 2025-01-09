import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import GithubMirrorModal from "@/components/GithubMirrorModal.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("github-mirror", ["identifier", "defaultRepoName"]);
createApp(GithubMirrorModal, props).mount("#github-mirror");
