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

export interface MetricsData {
  start_year: Metric;
  total_members: Metric;
  full_members: Metric;
  total_codebases: Metric;
  codebases_by_os: Metric;
  codebases_by_platform: Metric;
  codebases_by_language: Metric;
  reviewed_codebases: Metric;
  total_downloads: Metric;
}

const el = document.getElementById("app");
if (el) {
  const metrics: MetricsData = JSON.parse(el.getAttribute("data-metrics-data"));
  console.table(metrics);

  new MetricsPage({
    propsData: { metrics },
  }).$mount("#app");
}
