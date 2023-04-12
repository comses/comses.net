import "@/pages/sentry";
import MetricsPage from "@/pages/metrics/Metrics.vue";

const el = document.getElementById("app");
if (el) {
  // const metricsData = JSON.parse(el.getAttribute("data-all-metrics-data"))
  const MetricsData = JSON.parse(el.getAttribute("data-reformed-metrics-data"))

  console.log("MetricsData");
  console.log(JSON.stringify(MetricsData, null, 4));

  const dataMembersTotal = MetricsData.data_members_total;
  const dataMembersFull = MetricsData.data_members_full;
  const dataCodebasesTotal = MetricsData.data_codebases_total // TODO
  const dataCodebasesReviewed = MetricsData.data_codebases_reviewed;
  const seriesCodebasesOS = MetricsData.series_codebases_os;
  const seriesCodebasesPlatform = MetricsData.series_codebases_platform;
  const seriesCodebasesLangs = MetricsData.series_codebases_langs;
  const dataDownloadsTotal = MetricsData.data_downloads_total;

  // Initial highchart object
  const chartOptions = {
    title: {
      text: "Members", // default
      align: "left",
    },
    yAxis: {
      title: {
        text: "Members",
      },
    },
    plotOptions: {
      series: {
        label: {
          connectorAllowed: false,
        },
        pointStart: dataMembersTotal.start_year,
        stacking: undefined,
      },
    },
    series: [
      dataMembersTotal, // default data
    ],
  };

  new MetricsPage({
    propsData: {
      dataMembersTotal,
      dataMembersFull,
      seriesCodebasesOS,
      seriesCodebasesPlatform,
      seriesCodebasesLangs,
      dataCodebasesReviewed,
      dataDownloadsTotal,
      chartOptions
    }
  }).$mount("#app");
}

