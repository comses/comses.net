import "@/pages/sentry";
import MetricsPage from "@/pages/metrics/Metrics.vue";

export interface TimeSeries {
  name: string;
  data: number[];
  type?: string;
}

export interface Metric {
  title: string;
  yLabel: string;
  startYear: number;
  series: TimeSeries[];
}

export type MetricsData = Record<
  | "startYear"
  | "totalMembers"
  | "fullMembers"
  | "totalCodebases"
  | "codebasesByOs"
  | "codebasesByPlatform"
  | "codebasesByLanguage"
  | "reviewedCodebases"
  | "totalDownloads",
  Metric
>;

const el = document.getElementById("app");
if (el) {
  const metrics: MetricsData = JSON.parse(el.getAttribute("data-metrics-data"));

  new MetricsPage({
    propsData: { metrics },
  }).$mount("#app");
}
