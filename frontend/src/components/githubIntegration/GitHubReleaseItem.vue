<template>
  <li class="list-group-item border-0 p-2 rounded" :class="itemClass">
    <div class="d-flex flex-column gap-1">
      <div class="d-flex align-items-center gap-2">
        <a :href="release.htmlUrl" target="_blank">
          <i class="fab fa-github"></i>
        </a>
        <h6 class="mb-0 fw-bold">{{ release.name || release.tagName }}</h6>
        <span class="badge bg-gray">
          <i class="fas fa-tag"></i>
          {{ release.tagName }}
        </span>
      </div>
      <div class="text-muted small">
        Released {{ (release.publishedAt || release.createdAt)?.split("T")[0] }}
      </div>
    </div>
  </li>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { GitHubRelease } from "@/types";

export interface GitHubReleaseItemProps {
  release: GitHubRelease;
  codebaseIdentifier: string;
}

const props = defineProps<GitHubReleaseItemProps>();

const isOriginal = computed(() => !props.release.createdByIntegration);
const itemClass = computed(() => (isOriginal.value ? "bg-blue-gray" : "border"));
</script>
