<template>
  <div class="card">
    <ul class="list-group list-group-flush">
      <!-- Members -->
      <li class="list-group-item">
        <div class="form-check">
          <input
            class="form-check-input"
            type="radio"
            id="total-members"
            value="total-members"
            v-model="value"
          />
          <label class="form-check-label fw-bold" for="total-members"
            >Members <small class="text-muted">(total)</small></label
          >
        </div>
        <div class="ms-4 my-2">
          <div class="form-check">
            <input
              class="form-check-input"
              type="radio"
              id="full-members"
              value="full-members"
              v-model="value"
            />
            <label class="form-check-label" for="full-members"><small>Full Members</small></label>
          </div>
        </div>
      </li>
      <!-- Codebases -->
      <li class="list-group-item">
        <div class="form-check">
          <input
            class="form-check-input"
            type="radio"
            id="total-codebases"
            value="total-codebases"
            v-model="value"
          />
          <label class="form-check-label fw-bold" for="total-codebases"
            >Codebases <small class="text-muted">(total)</small></label
          >
        </div>
        <div class="ms-4 my-2">
          <div class="form-check mb-1">
            <input
              class="form-check-input"
              type="radio"
              id="reviewed-codebases"
              value="reviewed-codebases"
              v-model="value"
            />
            <label class="form-check-label" for="reviewed-codebases"
              ><small>Peer Reviewed</small></label
            >
          </div>
          <div class="form-check mb-1">
            <input
              class="form-check-input"
              type="radio"
              id="codebases-by-language"
              value="codebases-by-language"
              v-model="value"
            />
            <label class="form-check-label" for="codebases-by-language"
              ><small>By Language</small></label
            >
          </div>
          <div class="form-check mb-1">
            <input
              class="form-check-input"
              type="radio"
              id="codebases-by-platform"
              value="codebases-by-platform"
              v-model="value"
            />
            <label class="form-check-label" for="codebases-by-platform"
              ><small>By Platform</small></label
            >
          </div>
          <div class="form-check">
            <input
              class="form-check-input"
              type="radio"
              id="codebases-by-os"
              value="codebases-by-os"
              v-model="value"
            />
            <label class="form-check-label" for="codebases-by-os"
              ><small>By Operating System</small></label
            >
          </div>
        </div>
      </li>
      <!-- Downloads -->
      <li class="list-group-item">
        <div class="form-check">
          <input
            class="form-check-input"
            type="radio"
            id="total-downloads"
            value="total-downloads"
            v-model="value"
          />
          <label class="form-check-label fw-bold" for="total-downloads"
            >Downloads <small class="text-muted">(total)</small></label
          >
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { MetricsChartSelection } from "@/types";

const props = defineProps(["modelValue"]);
const emit = defineEmits(["update:modelValue"]);

const value = computed<MetricsChartSelection>({
  get() {
    return props.modelValue;
  },
  set(value) {
    emit("update:modelValue", value);
  },
});
</script>
