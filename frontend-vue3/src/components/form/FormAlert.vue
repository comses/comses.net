<template>
  <div class="card border-light" v-if="validationErrors.length > 0 || serverErrors.length > 0">
    <div class="card-body px-0 py-0">
      <div
        v-for="m in serverErrors.concat(validationErrors)"
        :key="m"
        class="alert alert-danger alert-dismissible fade show"
      >
        {{ m }}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface CheckboxProps {
  validationErrors: string[];
  serverErrors: string[];
}

const props = defineProps<CheckboxProps>();
</script>
