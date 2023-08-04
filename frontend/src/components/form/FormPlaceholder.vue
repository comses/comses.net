<template>
  <div class="placeholder-glow form-control">
    <span v-for="i in rows" :key="i">
      <span :class="`form-placeholder col-${randomColLength()}`" />
      <div class="w-100" />
    </span>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{ rows?: number }>(), {
  rows: 1,
});

function randomColLength() {
  const min = props.rows > 1 ? 0 : 4;
  const max = props.rows > 1 ? 10 : 10;
  return Math.floor(Math.random() * (max - min + 1) + min);
}
</script>
