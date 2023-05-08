<template>
  <i
    :class="`${iconClass} text-info`"
    data-bs-toggle="tooltip"
    :data-bs-placement="placement"
    :data-bs-custom-class="tooltipClass"
    :data-bs-title="title"
    title="Tooltip"
    ref="info"
  ></i>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Tooltip } from "bootstrap";

interface TooltipProps {
  title: string;
  iconClass?: string; // e.g. "fas fa-info-circle"
  tooltipClass?: string;
  placement?: string;
}

const props = withDefaults(defineProps<TooltipProps>(), {
  placement: "top",
  iconClass: "fas fa-info-circle",
  tooltipClass: "custom-tooltip",
});

const info = ref(null);
// eslint-disable-next-line @typescript-eslint/no-unused-vars
let tooltip: Tooltip | undefined;

onMounted(() => {
  tooltip = new Tooltip(info.value!);
});
</script>
