import "@/pages/sentry";
import MetricsPage from "@/pages/metrics/Metrics.vue";

export interface TimeSeries {
  name: string;
  data: number[];
  type?: string;
}

export interface Metric {
  title: string;
  y_label: string;
  start_year: number;
  series: TimeSeries[];
}

export type MetricsData = Record<
  | "start_year"
  | "total_members"
  | "full_members"
  | "total_codebases"
  | "codebases_by_os"
  | "codebases_by_platform"
  | "codebases_by_language"
  | "reviewed_codebases"
  | "total_downloads",
  Metric
>;

const el = document.getElementById("app");
if (el) {
  const metrics: MetricsData = JSON.parse(el.getAttribute("data-metrics-data"));

  new MetricsPage({
    propsData: { metrics },
  }).$mount("#app");
}
