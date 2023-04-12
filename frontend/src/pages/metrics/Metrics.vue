<template>
  <div>
    <!-- Box 1 -->
    <div class="metrics-box1">
      <div class="metrics-group">
        <div>
          <div class="radio-button">
            <input type="radio" id="members" value="Members" 
              v-model="picked" 
              @change="updateChartOptions" selected />
            <label for="members" class="radio-label"> Members by year</label>
            <div class="checkbox">
              <input type="checkbox" id="fullMembers" 
                v-model="selectedFullMembers" 
                @change="updateChartOptions" 
                :disabled="picked!='Members'"/>
              <label for="fullMembers" style="margin-left: 5px">Full Members</label>
            </div>
          </div>

          <div class="radio-button">
            <input type="radio" id="codebases" value="Codebases" 
              v-model="picked" @change="updateChartOptions"/>
            <label for="codebases" class="radio-label"> Codebases by year</label>

            <div class="checkbox">
              <input type="checkbox" id="language" 
                v-model="selectedLanguage" 
                @change="updateChartOptions"
                :disabled="picked!='Codebases' || selectedPeerReview == true"/>
              <label for="language" style="margin-left: 5px">By language</label>
              <br style="display: block; margin: 5px 0" />

              <input type="checkbox" id="peer" 
                v-model="selectedPeerReview" 
                @change="updateChartOptions"
                :disabled="picked!='Codebases' || selectedLanguage == true"/>
              <label for="peer" style="margin-left: 5px">Peer reviewed</label>
            </div>
          </div>

          <div class="radio-button">
            <input type="radio" id="downloads" value="Downloads" 
              v-model="picked"
              @change="updateChartOptions" />
            <label for="downloads" class="radio-label"> Downloads by year</label>
          </div>
        </div>
      </div>
    </div>

    <!-- Box 2 -->
    <div class="metrics-box2">
      <div class="tab">
        <button
          class="tab-button"
          :class="{ active: selectedTab === 'graph' }"
          @click="selectedTab = 'graph'"
        >
          Graph
        </button>
        <button
          class="tab-button"
          :class="{ active: selectedTab === 'data' }"
          @click="selectedTab = 'data'"
        >
          Data Table
        </button>
      </div>
      <div v-if="selectedTab === 'graph'">
        <highcharts :options="chartOptions"></highcharts>
      </div>
      <div v-if="selectedTab === 'data'">
        <!-- Data content -->
      </div>
    </div>
    <div class="clearfix" style="clear: both"></div>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop, Watch } from "vue-property-decorator";
import { Chart } from "highcharts-vue";
// import { Watch } from "fs";

@Component({
  // language=Vue
  components: {
    highcharts: Chart,
  },
})

export default class MetricsPage extends Vue {
  @Prop()
  public dataMembersTotal;
  @Prop()
  public dataMembersFull;
  @Prop()
  public seriesCodebasesOS;
  @Prop()
  public seriesCodebasesPlatform;
  @Prop()
  public seriesCodebasesLangs;
  @Prop()
  dataCodebasesReviewed;
  @Prop()
  public dataDownloadsTotal;
  @Prop()
  public chartOptions;

  public picked = "Members";
  public selectedLanguage = false;
  public selectedPeerReview = false;
  public selectedFullMembers = false;
  public selectedTab = "graph";
  public title: string = "Members";

  public dataCodebasesTotal: Object = {
    name: "total codebases",
    data: [100, 110, 120, 130, 140],
    start_year: 2008,
  };

  updateChartOptions() {
    switch (this.picked) {
      case "Members":
        this.chartOptions["title"]["text"] = "Members";
        this.chartOptions["plotOptions"]["series"]["stacking"] = undefined;
        this.chartOptions["plotOptions"]["series"]["pointStart"] = this.dataMembersTotal.start_year;
        if (this.selectedFullMembers) {
          this.chartOptions["series"] = [this.dataMembersTotal, this.dataMembersFull];
        } else {
          this.chartOptions["series"] = [this.dataMembersTotal];
        }
        break;
      case "Codebases":
        this.chartOptions["title"]["text"] = "Codebases";
        this.chartOptions["plotOptions"]["series"]["stacking"] = undefined;
        this.chartOptions["plotOptions"]["series"]["pointStart"] = this.dataCodebasesTotal["start_year"];
        if (this.selectedLanguage) {
          this.chartOptions["series"] = this.seriesCodebasesLangs;
          this.chartOptions["plotOptions"]["series"]["stacking"] = "normal";
          this.chartOptions["plotOptions"]["series"]["pointStart"] = this.seriesCodebasesLangs[0].start_year;
        } else if (this.selectedPeerReview) {
          this.chartOptions["plotOptions"]["series"]["pointStart"] = this.dataCodebasesReviewed.start_year;
          this.chartOptions["series"] = [this.dataCodebasesTotal, this.dataCodebasesReviewed];
        } else {
          this.chartOptions["series"] = [this.dataCodebasesTotal];
        }
        break;
      case "Downloads":
        this.chartOptions["title"]["text"] = "Downloads";
        this.chartOptions["series"] = [this.dataDownloadsTotal];
        this.chartOptions["plotOptions"]["series"]["stacking"] = undefined;
        break;
      default:
    }
  }

  data() {
    return {

    };
  }
}
</script>

<style scoped>
.metrics-box1 {
  border: 0.4px solid black;
  padding: 10px;
  box-sizing: border-box;
  width: 20%;
  float: left;
}

.metrics-group {
  margin: 10px 0;
}
.radio-button {
  margin-left: 0px;
}

.radio-label {
  margin-left: 5px;
}

.checkbox {
  margin-left: 20px;
}

.metrics-box2 {
  border: 0.4px solid black;
  padding: 10px;
  box-sizing: border-box;
  width: 70%;
  float: left;
}

.tab {
  display: flex;
  border-bottom: 1px solid #dee2e6;
}

.tab-button {
  color: #22b1e6;
  text-decoration: none;
  background-color: transparent;
  cursor: pointer;
  border: 1px solid transparent;
  display: block;
  padding: 0.5rem 1rem;
}

.tab-button.active {
  color: #495057;
  background-color: #fff;
  border-color: #dee2e6 #dee2e6 #fff;
  box-sizing: border-box;
  margin-bottom: -1px;
}
</style>
