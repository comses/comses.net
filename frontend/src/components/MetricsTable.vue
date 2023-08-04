<template>
  <table class="table">
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
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { TimeSeries } from "@/types";

const props = defineProps<{
  series: TimeSeries[];
  plotOptions: any;
}>();

const startYear = computed(() => {
  return props.plotOptions.series.pointStart;
});

const tableHeaders = computed(() => {
  return ["Year", ...props.series.map((s: any) => s.name)];
});

const tableRows = computed(() => {
  return props.series[0].data.map((_, i: number) => [
    startYear.value + i,
    ...props.series.map((s: TimeSeries) => s.data[i]),
  ]);
});
</script>
