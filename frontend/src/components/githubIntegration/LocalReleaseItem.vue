<template>
  <li
    class="list-group-item"
    :class="{
      'opacity-50': !release.live || release.importedReleaseSyncState,
    }"
  >
    <div class="d-flex align-items-center justify-content-between mb-2">
      <div class="d-flex align-items-center gap-2">
        <a :href="release.absoluteUrl" target="_blank"><i class="fas fa-external-link-alt"></i></a>
        <h6 class="mb-0 fw-bold">v{{ release.versionNumber }}</h6>
        <span v-if="release.status === 'UNDER_REVIEW'" class="badge bg-danger">Under Review</span>
        <span v-if="release.importedReleaseSyncState && !release.live">
          <a :href="editHref" class="text-decoration-underline small">
            Edit metadata and publish release
          </a>
        </span>
        <span v-else-if="release.importedReleaseSyncState" class="badge bg-secondary"
          ><i class="fas fa-download"></i> Imported</span
        >
        <span v-else-if="!release.live" class="badge bg-dark"
          ><i class="fas fa-lock"></i> Private</span
        >
      </div>
      <div class="d-flex align-items-center gap-2">
        <div v-if="release.gitRefSyncState" class="d-flex align-items-center gap-1">
          <span class="badge" :class="statusBadgeClass">{{ statusLabel }}</span>
          <BootstrapTooltip
            v-if="release.gitRefSyncState.status === 'ERROR' && errorMessage"
            :title="errorMessage"
            icon-class="fas fa-exclamation-triangle text-danger"
            placement="bottom"
          />
        </div>
        <span v-if="release.gitRefSyncState?.canPush" class="badge bg-primary">
          {{ release.gitRefSyncState?.status === "SUCCESS" ? "Metadata updates" : "Can push" }}
        </span>
      </div>
    </div>

    <div class="d-flex align-items-center gap-2 text-muted small mb-2">
      <span>Published {{ release.firstPublishedAt || release.dateCreated }}</span>
    </div>
    <div v-if="isInProgress" class="mt-2">
      <div class="d-flex align-items-center justify-content-between text-muted small mb-1">
        <span>Syncing to GitHub...</span>
        <span>{{ progress }}%</span>
      </div>
      <div class="progress" style="height: 4px">
        <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
      </div>
    </div>
  </li>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useReleaseEditorAPI } from "@/composables/api/releaseEditor";
import type { CodebaseReleaseWithGitRefSyncState } from "@/types";
import BootstrapTooltip from "@/components/BootstrapTooltip.vue";

export interface LocalReleaseItemProps {
  release: CodebaseReleaseWithGitRefSyncState;
  isInProgress: boolean;
  progress: number;
}

const props = defineProps<LocalReleaseItemProps>();

const { editUrl } = useReleaseEditorAPI();

const statusLabel = computed(() => {
  const state = props.release.gitRefSyncState;
  if (!state) return "";
  switch (state.status) {
    case "RUNNING":
      return "In Progress";
    case "ERROR":
      return "Failed";
    case "SUCCESS":
      return "Success";
    case "PENDING":
      return "Pending";
    default:
      return null;
  }
});

const statusBadgeClass = computed(() => {
  const state = props.release.gitRefSyncState;
  if (!state) return null;
  switch (state.status) {
    case "RUNNING":
      return "bg-warning";
    case "ERROR":
      return "bg-danger";
    case "SUCCESS":
      return "bg-success";
    case "PENDING":
      return "bg-gray";
    default:
      return null;
  }
});

const editHref = computed(() =>
  editUrl(props.release.codebase.identifier, props.release.versionNumber)
);

const errorMessage = computed(() => props.release.gitRefSyncState?.errorMessage || "");
</script>
