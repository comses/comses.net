<template>
  <div>
      <highcharts :options="chartOptions"></highcharts>
  </div>
</template>

<script>
import { Component, Vue } from "vue-property-decorator";
import {HighchartsVue} from "highcharts-vue";
import {Chart} from "highcharts-vue";

@Component({
  // language=Vue
  components: {
    "highcharts": Chart,
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
        series: [{
          data: [10, 0, 8, 2, 6, 4, 5, 5]
        }]
      };
}
</script>

<style scoped></style>
