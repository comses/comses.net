<template>
  <div>
    <highcharts :options="chartOptions"></highcharts>

    <!-- Box 1 -->
    <div class="metrics-box1">
      <div class="metrics-group">
        <div>
          <div class="radio-button">
            <input type="radio" id="members" value="Members" v-model="picked" />
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
        <!-- Graph content  -->
      </div>
      <div v-if="selectedTab === 'data'">
        <!-- Data content -->
      </div>
    </div>

    <div class="clearfix" style="clear: both"></div>
  </div>
</template>

<script>
import { Component, Vue } from "vue-property-decorator";
import { HighchartsVue } from "highcharts-vue";
import { Chart } from "highcharts-vue";

@Component({
  // language=Vue
  components: {
    highcharts: Chart,
  },
})
export default class MetricsPage extends Vue {
  chartOptions = {
    // chart: {
    //   type: 'spline'
    // },
    // title: {
    //   text: 'Entire title'
    // },
    series: [
      {
        data: [10, 0, 8, 2, 6, 4, 5, 5],
      },
    ],
  };

  data() {
    return {
      picked: null,
      selectedLanguage: false,
      selectedPeerReview: false,
      selectedFullMembers: false,
      selectedTab: "graph",
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
