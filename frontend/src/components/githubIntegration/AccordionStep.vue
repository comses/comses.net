<template>
  <div class="accordion-item border rounded mb-3">
    <h5 class="accordion-header">
      <div class="d-flex align-items-center justify-content-between p-3">
        <div class="d-flex align-items-center gap-3">
          <i class="text-muted" :class="isCompleted ? 'fas fa-check-circle' : 'far fa-circle'"></i>
          <div
            class="fw-bold"
            :class="{
              'text-dark': isExpanded,
              'text-muted': !isExpanded,
            }"
          >
            <!-- title slot -->
            <slot name="title" :is-completed="isCompleted" :is-expanded="isExpanded" />
          </div>
        </div>
        <!-- actions slot (edit buttons, etc.) -->
        <div v-if="$slots.actions">
          <slot name="actions" :is-completed="isCompleted" :is-expanded="isExpanded" />
        </div>
      </div>
    </h5>
    <div class="accordion-collapse collapse" :class="{ show: isExpanded }">
      <div class="accordion-body">
        <div class="p-3">
          <!-- main content when expanded -->
          <slot name="content" :is-completed="isCompleted" :is-expanded="isExpanded" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

export interface AccordionStepProps {
  isCompleted: boolean;
  collapse?: boolean;
}

const props = withDefaults(defineProps<AccordionStepProps>(), {
  collapse: false,
});

const isExpanded = computed(() => (props.collapse ? false : !props.isCompleted));
</script>
