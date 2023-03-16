<template>
  <h1>Vue 3 Component</h1>
  <p>Vue 3 with Vite HMR proof of concept, count: {{ count }}</p>
  <button @click="log">click me to say hello</button>
</template>

<script setup lang="ts">
import { useCount } from "@/composables/count";

const msg = "Hello world";
const { count, increment } = useCount();

function log() {
  increment();
  console.log(msg, count.value);
}
</script>
