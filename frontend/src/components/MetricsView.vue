<template>
  <div class="row">
    <div class="col-sm-12 col-md-3" style="padding-top: 2.5rem">
      <MetricsSelector v-model="selectedChart" />
    </div>
    <div class="col-sm-12 col-md-9">
      <ul class="nav nav-tabs">
        <li class="nav-item">
          <a
            :class="{ 'nav-link': true, active: selectedTab === 'chart' }"
            @click="selectedTab = 'chart'"
            >Chart</a
          >
        </li>
        <li class="nav-item">
          <a
            :class="{ 'nav-link': true, active: selectedTab === 'table' }"
            @click="selectedTab = 'table'"
            >Table</a
          >
        </li>
      </ul>
      <div class="border border-top-0">
        <span v-if="chartOptionsMap">
          <Chart v-if="selectedTab === 'chart'" :options="chartOptions" class="pt-2" />
          <MetricsTable
            v-else
            :series="chartOptions.series"
            :plot-options="chartOptions.plotOptions"
          />
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Highcharts from "highcharts";
import exportingInit from "highcharts/modules/exporting";
import labelInit from "highcharts/modules/series-label";
import { Chart } from "highcharts-vue";
import { ref, computed, onMounted } from "vue";
import type { MetricsData, MetricsChartSelection, Metric } from "@/types";
import MetricsSelector from "@/components/MetricsSelector.vue";
import MetricsTable from "@/components/MetricsTable.vue";

exportingInit(Highcharts); // required for hamburger menu w/ download options
labelInit(Highcharts); // required for series labels on area charts

const props = defineProps<{
  metricsData: MetricsData;
}>();

const chartOptionsMap = ref<Map<MetricsChartSelection, any>>();
const selectedChart = ref<MetricsChartSelection>("total-members");
const selectedTab = ref<"chart" | "table">("chart");

const chartOptions = computed(() => {
  if (!chartOptionsMap.value) return;
  return chartOptionsMap.value.get(selectedChart.value);
});

onMounted(() => {
  initalizeChartMap();
});

function initalizeChartMap() {
  chartOptionsMap.value = new Map<MetricsChartSelection, any>([
    ["total-members", createCumulativeChart(props.metricsData.totalMembers)],
    ["full-members", createCumulativeChart(props.metricsData.fullMembers)],
    ["total-releases", createCumulativeChart(props.metricsData.totalReleases)],
    ["reviewed-releases", createCumulativeChart(props.metricsData.reviewedReleases)],
    ["releases-by-os", createAreaPercentageChart(props.metricsData.releasesByOs)],
    ["releases-by-language", createAreaPercentageChart(props.metricsData.releasesByLanguage)],
    ["releases-by-platform", createAreaPercentageChart(props.metricsData.releasesByPlatform)],
    ["total-downloads", createCumulativeChart(props.metricsData.totalDownloads)],
  ]);
}

function cumulativeSum(array: number[]) {
  return array.map(
    (
      (sum: number) => (value: number) =>
        (sum += value)
    )(0)
  );
}

function createBaseChartOptions(metric: Metric): any {
  return {
    title: {
      text: metric.title,
    },
    yAxis: {
      title: {
        text: metric.yLabel,
      },
    },
    xAxis: {},
    plotOptions: {
      series: {
        pointStart: metric.startYear,
        label: {
          enabled: false,
        },
      },
    },
    chart: {
      height: "70%",
    },
  };
}

function createCumulativeChart(metric: Metric) {
  const seriesCumulative = metric.series.map(s => {
    return {
      ...s,
      type: "spline",
      data: cumulativeSum(s.data),
      pointStart: metric.startYear,
    };
  });

  const seriesNew = metric.series.map(s => {
    return {
      ...s,
      name: `New ${s.name}`,
      type: "column",
      pointStart: metric.startYear,
    };
  });

  const chartOptions = {
    ...createBaseChartOptions(metric),
    series: [...seriesNew, ...seriesCumulative],
  };
  const currentYear = new Date().getFullYear();
  // cut-off band to incidate that the current year is incomplete
  chartOptions.xAxis.plotBands = [
    {
      color: "#f2f2f2",
      from: currentYear - 0.5,
      to: currentYear + 1,
    },
  ];

  return chartOptions;
}

function createAreaPercentageChart(metric: Metric) {
  const series = metric.series.map(s => {
    return {
      ...s,
      type: "areaspline",
      pointStart: metric.startYear,
    };
  });

  const chartOptions = {
    ...createBaseChartOptions(metric),
    series,
  };
  chartOptions.plotOptions.areaspline = {
    stacking: "percent",
    marker: {
      enabled: false,
    },
  };
  chartOptions.plotOptions.series.label.enabled = true;
  chartOptions.tooltip = {
    split: true,
  };

  return chartOptions;
}
</script>
