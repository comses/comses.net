<template>
  <h1>Vue 3 Component</h1>
  <p>Vue 3 with Vite HMR proof of concept</p>
  <button @click="log">click me to say hello</button>
</template>

<script setup lang="ts">
const msg = "Hello world";

function log() {
  console.log(msg);
}
</script>
