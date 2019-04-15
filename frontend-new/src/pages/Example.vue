<template>
  <div class="foo">
    {{ state }}
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class Example extends Vue {
  public data() {
    return {
      state: 'Hello!'
    };
  }
}
</script>
