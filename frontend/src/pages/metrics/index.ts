import "@/pages/sentry";
import MetricsPage from "@/pages/metrics/Metrics.vue";

const el = document.getElementById("app");
if (el) {
  // const metricsData = JSON.parse(el.getAttribute("data-all-metrics-data"))
  const metricsData = JSON.parse(el.getAttribute("data-metrics-data"));

  console.log("metricsData");
  console.log(JSON.stringify(metricsData, null, 4));

  const dataMembersTotal = metricsData.data_members_total;
  const dataMembersFull = metricsData.data_members_full;
  const dataCodebasesTotal = metricsData.data_codebases_total; // TODO
  const dataCodebasesReviewed = metricsData.data_codebases_reviewed;
  const seriesCodebasesOS = metricsData.series_codebases_os;
  const seriesCodebasesPlatform = metricsData.series_codebases_platform;
  const seriesCodebasesLangs = metricsData.series_codebases_langs;
  const dataDownloadsTotal = metricsData.data_downloads_total;

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
      dataCodebasesTotal,
      seriesCodebasesOS,
      seriesCodebasesPlatform,
      seriesCodebasesLangs,
      dataCodebasesReviewed,
      dataDownloadsTotal,
      chartOptions,
    },
  }).$mount("#app");
}
