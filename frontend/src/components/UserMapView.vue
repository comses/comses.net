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

/*
const institutionData = [
  {
    name: "University of Botswana",
    lat: -24.65451,
    lon: 25.90859,
    value: 1,
  },
  {
    name: "Arizona State University",
    lat: 33.41477,
    lon: -111.90931,
    value: 33,
  },
  {
    name: "Institute of Archaeology",
    lat: 48.306808,
    lon: 18.099056,
    value: 1,
  },
  {
    name: "Punjabi University",
    lat: 30.359724,
    lon: 76.454228,
    value: 1,
  },
  {
    name: "University of Queensland",
    lat: -27.46794,
    lon: 153.02809,
    value: 2,
  },
  {
    name: "University of Essex",
    lat: 51.877938,
    lon: 0.947196,
    value: 2,
  },
  {
    name: "Drexel University",
    lat: 39.95238,
    lon: -75.16362,
    value: 1,
  },
  {
    name: "Cairo University",
    lat: 30.0276,
    lon: 31.21014,
    value: 2,
  },
  {
    name: "University of Bamberg",
    lat: 49.89873,
    lon: 10.90067,
    value: 2,
  },
];
*/
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
      color: "#E0E0E0",
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
        fillColor: "#CC2936",
        lineColor: "#00000000",
      },
      colorAxis: false,
      zIndex: 1,
    },
  ],
};
</script>