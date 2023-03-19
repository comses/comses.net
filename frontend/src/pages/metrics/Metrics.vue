<template>
  <div>
    <!-- Box 1 -->
    <div class="metrics-box1">
      <div class="metrics-group">
        <div>
          <div class="radio-button">
            <input type="radio" id="members" value="Members" v-model="picked" selected/>
            <label for="members" class="radio-label"> Members by year</label>
            <div class="checkbox">
              <input type="checkbox" id="fullMembers" v-model="selectedFullMembers" />
              <label for="fullMembers" style="margin-left: 5px">Full Members</label>
            </div>
          </div>

          <div class="radio-button">
            <input type="radio" id="codebases" value="Codebases" v-model="picked" />
            <label for="codebases" class="radio-label"> Codebases by year</label>

            <div class="checkbox">
              <input type="checkbox" id="language" v-model="selectedLanguage" />
              <label for="language" style="margin-left: 5px">By language</label>
              <br style="display: block; margin: 5px 0" />

              <input type="checkbox" id="peer" v-model="selectedPeerReview" />
              <label for="peer" style="margin-left: 5px">Peer reviewed</label>
            </div>
          </div>

          <div class="radio-button">
            <input type="radio" id="downloads" value="Downloads" v-model="picked" />
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
  public picked = "Members";
  public selectedLanguage = false;
  public selectedPeerReview = false;
  public selectedFullMembers = false;
  public selectedTab = "graph";
  public title: string = "Members";
  // mock data
  public dataMembersTotal: Object = {
      name: "total members",
      data: [90, 100, 110, 120, 130],
  };
  public dataMembersFull: Object = {
      name: "full members",
      data: [70, 80, 90, 100, 110],
  };
  public dataCodebasesTotal: Object = {
      name: "total codebases",
      data: [100, 110, 120, 130, 140]
  };
  public dataCodebasesReviewed: Object = {
      name: "reviewed codebases",
      data: [70, 80, 90, 100, 110]
  };
  public seriesCodebasesLangs: Array<Object> = [
    {
      name: "Netlog",
      data: [40, 30, 30, 40, 40]
    },
    {
      name: "Python",
      data: [20, 30, 30, 30, 40]
    },
    {
      name: "Julia",
      data: [20, 30, 30, 30, 30]
    },
    {
      name: "C",
      data: [20, 20, 30, 30, 30]
    },
  ]
  // public seriesCodebasesPlatform: Array = []
  public dataDownloadsTotal: Object = {
      name: "total downloads",
      data: [50, 60, 70, 80, 90]
  };
  public chartOptions: Object = {
      // chart: {
      //   type: 'spline'
      // },
      title: {
          text: "Members", // default
          align: 'left'
      },
      yAxis: {
          title: {
              text: 'Members'
          }
      },
      xAxis: {
          accessibility: {
              rangeDescription: 'Range: 2019 to 2023'
          }
      },
      plotOptions: {
          series: {
              label: {
                  connectorAllowed: false
              },
              pointStart: 2019
          }
      },
      series: [
        this.dataMembersTotal // default data
      ],
    };

  @Watch('picked')
  @Watch('selectedFullMembers')
  @Watch('selectedLanguage')
  @Watch('selectedPeerReview')
  updateChartOptions() {
    console.log("updateChartOptions");
    switch (this.picked){
      case "Members":
        this.chartOptions["title"]["text"] = "Members";
        if (this.selectedFullMembers) {
          this.chartOptions["series"] = [this.dataMembersTotal, this.dataMembersFull];
        } else {
          this.chartOptions["series"] = [this.dataMembersTotal];
        }
        break;
      case "Codebases":
        this.chartOptions["title"]["text"] = "Codebases";
        if (this.selectedLanguage) {
          this.chartOptions["series"] = this.seriesCodebasesLangs;
        } else if (this.selectedPeerReview) {
          this.chartOptions["series"] = [this.dataCodebasesTotal, this.dataCodebasesReviewed];
        } else {
          this.chartOptions["series"] = [this.dataCodebasesTotal];
        }
        break;
      case "Downloads":
        this.chartOptions["title"]["text"] = "Downloads";
        this.chartOptions["series"] = [this.dataDownloadsTotal];
        break;
      default:
    }
  }


  data() {
    return {
      // picked: "Members",
      // selectedLanguage: false,
      // selectedPeerReview: false,
      // selectedFullMembers: false,
      // selectedTab: "graph",
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
  margin-bottom: 10px;
  
}

.tab-button {
  border: none;
  outline: none;
  background-color: white;
  cursor: pointer;
  padding: 5px;
  margin-right: 10px;
}

.tab-button.active {
  background-color: #269abc;
  color: white;
  border-radius: 3px;
}
</style>
