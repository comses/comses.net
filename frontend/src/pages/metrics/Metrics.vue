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
                id="members"
                value="members"
                v-model="dataSelection"
              />
              <label class="form-check-label font-weight-bold" for="members"
                >Members <small class="text-muted">(total)</small></label
              >
            </div>
            <div class="ml-4 my-2">
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="radio"
                  id="members-full"
                  value="members-full"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="members-full"
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
                id="codebases"
                value="codebases"
                v-model="dataSelection"
              />
              <label class="form-check-label font-weight-bold" for="codebases"
                >Codebases <small class="text-muted">(total)</small></label
              >
            </div>
            <div class="ml-4 my-2">
              <div class="form-check mb-1">
                <input
                  class="form-check-input"
                  type="radio"
                  id="codebases-reviewed"
                  value="codebases-reviewed"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="codebases-reviewed"
                  ><small>Peer Reviewed</small></label
                >
              </div>
              <div class="form-check mb-1">
                <input
                  class="form-check-input"
                  type="radio"
                  id="codebases-language"
                  value="codebases-language"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="codebases-language"
                  ><small>By Language</small></label
                >
              </div>
              <div class="form-check mb-1">
                <input
                  class="form-check-input"
                  type="radio"
                  id="codebases-platform"
                  value="codebases-platform"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="codebases-platform"
                  ><small>By Platform</small></label
                >
              </div>
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="radio"
                  id="codebases-os"
                  value="codebases-os"
                  v-model="dataSelection"
                />
                <label class="form-check-label" for="codebases-os"
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
                id="downloads"
                value="downloads"
                v-model="dataSelection"
              />
              <label class="form-check-label font-weight-bold" for="downloads"
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
import { TimeSeries } from "@/pages/metrics";

exportingInit(Highcharts); // Initialize exporting module (hamburger menu w/ download options)

@Component({
  components: {
    Chart,
  },
})
export default class MetricsPage extends Vue {
  @Prop() chartOptionsMap: Map<string, any>;

  dataSelection = "members";
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
}
</script>
