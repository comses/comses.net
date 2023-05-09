import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import { extractDataParams } from "@/util";
import MetricsView from "@/components/MetricsView.vue";

const props = extractDataParams("metrics-view", ["metricsData"]);
createApp(MetricsView, props).mount("#metrics-view");
