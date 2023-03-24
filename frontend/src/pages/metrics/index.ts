import "@/pages/sentry";
import MetricsPage from "@/pages/metrics/Metrics.vue";

const el = document.getElementById("app");
if (el) {
  const metricsData = JSON.parse(el.getAttribute("data-all-metrics-data"))
  new MetricsPage({
    propsData: {
      metricsData
    }
  }).$mount("#app");
}

