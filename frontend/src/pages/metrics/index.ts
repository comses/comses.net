import "@/pages/sentry";
import MetricsPage from "@/pages/metrics/Metrics.vue";

export interface TimeSeries {
  name: string;
  data: number[];
  start_year: number;
}

export interface MetricsData {
  data_members_total: TimeSeries;
  data_members_full: TimeSeries;
  data_codebases_total: TimeSeries;
  data_codebases_reviewed: TimeSeries;
  series_codebases_os: TimeSeries[];
  series_codebases_platform: TimeSeries[];
  series_codebases_langs: TimeSeries[];
  data_downloads_total: TimeSeries;
}

const el = document.getElementById("app");
if (el) {
  const metrics: MetricsData = JSON.parse(el.getAttribute("data-metrics-data"));

  const chartOptionsMap = new Map([
    [
      "members",
      createCumulativeChart("Members", "Members", metrics.data_members_total.start_year, [
        metrics.data_members_total,
      ]),
    ],
    [
      "members-full",
      createCumulativeChart("Full Members", "Members", metrics.data_members_total.start_year, [
        metrics.data_members_total,
        metrics.data_members_full,
      ]),
    ],
    [
      "codebases",
      createCumulativeChart("Codebases", "Codebases", metrics.data_codebases_total.start_year, [
        metrics.data_codebases_total,
      ]),
    ],
    [
      "codebases-reviewed",
      createCumulativeChart(
        "Reviewed Codebases",
        "Codebases",
        metrics.data_codebases_total.start_year,
        [metrics.data_codebases_total, metrics.data_codebases_reviewed]
      ),
    ],
    [
      "codebases-os",
      createAreaPercentageChart(
        "Codebases by Operating System",
        "Codebases",
        metrics.series_codebases_os[0].start_year,
        metrics.series_codebases_os
      ),
    ],
    [
      "codebases-platform",
      createAreaPercentageChart(
        "Codebases by Platform/Framework",
        "Codebases",
        metrics.series_codebases_platform[0].start_year,
        metrics.series_codebases_platform
      ),
    ],
    [
      "codebases-language",
      createAreaPercentageChart(
        "Codebases by Language",
        "Codebases",
        metrics.series_codebases_langs[0].start_year,
        metrics.series_codebases_langs
      ),
    ],
    [
      "downloads",
      createCumulativeChart("Downloads", "Downloads", metrics.data_downloads_total.start_year, [
        metrics.data_downloads_total,
      ]),
    ],
  ]);

  new MetricsPage({
    propsData: { chartOptionsMap },
  }).$mount("#app");
}

function cumulativeSum(array: number[]) {
  return array.map(
    (
      (sum: number) => (value: number) =>
        (sum += value)
    )(0)
  );
}

function createCumulativeChart(
  title: string,
  yAxisTitle: string,
  startYear: number,
  series: any[]
) {
  const seriesCumulative = series.map(s => {
    return {
      ...s,
      type: "spline",
      data: cumulativeSum(s.data),
    };
  });

  const seriesNew = series.map(s => {
    return {
      ...s,
      name: `New ${s.name}`,
      type: "column",
    };
  });

  return {
    title: {
      text: title,
    },
    yAxis: {
      title: {
        text: yAxisTitle,
      },
    },
    plotOptions: {
      series: {
        pointStart: startYear,
      },
    },
    series: [...seriesNew, ...seriesCumulative],
  };
}

function createAreaPercentageChart(
  title: string,
  yAxisTitle: string,
  startYear: number,
  series: any[]
) {
  series.forEach(s => {
    s.type = "areaspline";
  });

  return {
    title: {
      text: title,
    },
    yAxis: {
      title: {
        text: yAxisTitle,
      },
    },
    plotOptions: {
      areaspline: {
        stacking: "percent",
        marker: {
          enabled: false,
        },
      },
      series: {
        pointStart: startYear,
      },
    },
    series,
  };
}
