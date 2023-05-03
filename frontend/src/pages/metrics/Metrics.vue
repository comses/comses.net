<template>
  <div class="row">
    <div class="col-sm-12 col-md-3" style="padding-top: 2.5rem">
      <div class="card">
        <ul class="list-group list-group-flush">
          <!-- Members -->
          <li class="list-group-item">
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="total-members"
                value="total-members"
                v-model="dataSelection"
              />
              <label class="form-check-label font-weight-bold" for="total-members"
                >Members <small class="text-muted">(total)</small></label
              >
            </div>
            <div class="ml-4 my-2">
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="radio"
                  id="full-members"
                  value="full-members"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="full-members"
                  ><small>Full Members</small></label
                >
              </div>
            </div>
          </li>
          <!-- Codebases -->
          <li class="list-group-item">
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="total-codebases"
                value="total-codebases"
                v-model="dataSelection"
              />
              <label class="form-check-label font-weight-bold" for="total-codebases"
                >Codebases <small class="text-muted">(total)</small></label
              >
            </div>
            <div class="ml-4 my-2">
              <div class="form-check mb-1">
                <input
                  class="form-check-input"
                  type="radio"
                  id="reviewed-codebases"
                  value="reviewed-codebases"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="reviewed-codebases"
                  ><small>Peer Reviewed</small></label
                >
              </div>
              <div class="form-check mb-1">
                <input
                  class="form-check-input"
                  type="radio"
                  id="codebases-by-language"
                  value="codebases-by-language"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="codebases-by-language"
                  ><small>By Language</small></label
                >
              </div>
              <div class="form-check mb-1">
                <input
                  class="form-check-input"
                  type="radio"
                  id="codebases-by-platform"
                  value="codebases-by-platform"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="codebases-by-platform"
                  ><small>By Platform</small></label
                >
              </div>
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="radio"
                  id="codebases-by-os"
                  value="codebases-by-os"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="codebases-by-os"
                  ><small>By Operating System</small></label
                >
              </div>
            </div>
          </li>
          <!-- Downloads -->
          <li class="list-group-item">
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="total-downloads"
                value="total-downloads"
                v-model="dataSelection"
              />
              <label class="form-check-label font-weight-bold" for="total-downloads"
                >Downloads <small class="text-muted">(total)</small></label
              >
            </div>
          </li>
        </ul>
      </div>
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
        <Chart v-if="selectedTab === 'chart'" :options="chartOptions" class="pt-2" />
        <table v-if="selectedTab === 'table'" class="table">
          <thead>
            <tr>
              <th v-for="head in tableHeaders" :key="head" scope="col">{{ head }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in tableRows" :key="index">
              <td v-for="(cell, index) in row" :key="index">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop } from "vue-property-decorator";
import Highcharts from "highcharts";
import exportingInit from "highcharts/modules/exporting";
import { Chart } from "highcharts-vue";
import { Metric, MetricsData, TimeSeries } from "@/pages/metrics";

exportingInit(Highcharts); // Initialize exporting module (hamburger menu w/ download options)

// key for the different charts, correpsonds to the radio button values
type ChartSelection =
  | "total-members"
  | "full-members"
  | "total-codebases"
  | "reviewed-codebases"
  | "codebases-by-language"
  | "codebases-by-platform"
  | "codebases-by-os"
  | "total-downloads";

@Component({
  components: {
    Chart,
  },
})
export default class MetricsPage extends Vue {
  @Prop() metrics: MetricsData;

  chartOptionsMap: Map<ChartSelection, any>;

  dataSelection: ChartSelection = "total-members";
  selectedTab: "chart" | "table" = "chart";

  get chartOptions() {
    return {
      ...this.chartOptionsMap.get(this.dataSelection),
      chart: {
        height: "70%",
      },
    };
  }

  get series() {
    return this.chartOptions.series;
  }

  get startYear() {
    return this.chartOptions.plotOptions.series.pointStart;
  }

  get tableHeaders() {
    return ["Year", ...this.chartOptions.series.map((s: TimeSeries) => s.name)];
  }

  get tableRows() {
    return this.series[0].data.map((_, i: number) => [
      this.startYear + i,
      ...this.series.map((s: TimeSeries) => s.data[i]),
    ]);
  }

  created() {
    this.initalizeChartMap();
  }

  initalizeChartMap() {
    this.chartOptionsMap = new Map<ChartSelection, any>([
      ["total-members", this.createCumulativeChart(this.metrics.total_members)],
      ["full-members", this.createCumulativeChart(this.metrics.full_members)],
      ["total-codebases", this.createCumulativeChart(this.metrics.total_codebases)],
      ["reviewed-codebases", this.createCumulativeChart(this.metrics.reviewed_codebases)],
      ["codebases-by-os", this.createAreaPercentageChart(this.metrics.codebases_by_os)],
      ["codebases-by-language", this.createAreaPercentageChart(this.metrics.codebases_by_language)],
      ["codebases-by-platform", this.createAreaPercentageChart(this.metrics.codebases_by_platform)],
      ["total-downloads", this.createCumulativeChart(this.metrics.total_downloads)],
    ]);
  }

  cumulativeSum(array: number[]) {
    return array.map(
      (
        (sum: number) => (value: number) =>
          (sum += value)
      )(0)
    );
  }

  createBaseChartOptions(metric: Metric): any {
    return {
      title: {
        text: metric.title,
      },
      yAxis: {
        title: {
          text: metric.y_label,
        },
      },
      xAxis: {},
      plotOptions: {
        series: {
          pointStart: metric.start_year,
        },
      },
    };
  }

  createCumulativeChart(metric: Metric) {
    const seriesCumulative = metric.series.map(s => {
      return {
        ...s,
        type: "spline",
        data: this.cumulativeSum(s.data),
        pointStart: metric.start_year,
      };
    });

    const seriesNew = metric.series.map(s => {
      return {
        ...s,
        name: `New ${s.name}`,
        type: "column",
        pointStart: metric.start_year,
      };
    });

    const chartOptions = {
      ...this.createBaseChartOptions(metric),
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

  createAreaPercentageChart(metric: Metric) {
    const series = metric.series.map(s => {
      return {
        ...s,
        type: "areaspline",
        pointStart: metric.start_year,
      };
    });

    const chartOptions = {
      ...this.createBaseChartOptions(metric),
      series,
    };
    chartOptions.plotOptions.areaspline = {
      stacking: "percent",
      marker: {
        enabled: false,
      },
    };

    return chartOptions;
  }
}
</script>
