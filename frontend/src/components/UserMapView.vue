<template>
  <Chart :constructor-type="'mapChart'" :options="mapChartOptions"></Chart>
</template>

<script setup lang="ts">
import Highcharts from "highcharts";
import exportingInit from "highcharts/modules/exporting";
import mapInit from "highcharts/modules/map";
import labelInit from "highcharts/modules/series-label";
import { Chart } from "highcharts-vue";
import world from "@/assets/world.geo.json";
import proj4 from "proj4";
import type { MetricsData, MetricsChartSelection, Metric } from "@/types";

exportingInit(Highcharts); // required for hamburger menu w/ download options
labelInit(Highcharts); // required for series labels on area charts
mapInit(Highcharts); // required for map charts

const props = defineProps<{
  metricsData: MetricsData;
}>();

const institutionData = props.metricsData.institutionData;

const mapChartOptions = {
  chart: {
    map: world,
    proj4,
  },

  legend: {
    enabled: false,
  },

  title: {
    text: "Member-affiliated Institutions",
  },

  mapNavigation: {
    enabled: true,
    buttonOptions: {
      verticalAlign: "bottom",
    },
  },

  series: [
    {
      // base map (countries under the bubbles)
      name: "countries",
      color: "#0000FF",
      enableMouseTracking: false,
      zIndex: 0,
      states: {
        inactive: {
          opacity: 1,
        },
      },
    },
    {
      type: "mapbubble",
      name: "Member-affiliated Institutions",
      data: institutionData.map(item => ({
        name: item.name,
        z: item.value,
        lat: item.lat,
        lon: item.lon,
      })),
      minSize: 4,
      maxSize: 20,
      marker: {
        fillColor: "#800080",
        lineColor: "#00000000",
      },
      colorAxis: true,
      zIndex: 1,
    },
  ],
};
</script>
