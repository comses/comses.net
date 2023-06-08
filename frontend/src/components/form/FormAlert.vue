<template>
  <div class="card border-0" v-if="validationErrors.length > 0 || serverErrors.length > 0">
    <div class="card-body px-0 py-0">
      <div
        v-if="validationErrors.length > 0"
        class="alert alert-warning alert-dismissible fade show mb-0 mt-3"
      >
        Form not submitted. Please check above for errors.
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" />
      </div>
      <div
        v-for="message in serverErrors"
        :key="message"
        class="alert alert-danger alert-dismissible fade show mb-0 mt-3"
      >
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface AlertProps {
  validationErrors: string[];
  serverErrors: string[];
}

const props = defineProps<AlertProps>();
</script>
