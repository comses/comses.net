<template>
  <li
    class="list-group-item"
    :class="{
      'opacity-50': release.createdByIntegration,
    }"
  >
    <div class="d-flex align-items-center justify-content-between mb-2">
      <div class="d-flex align-items-center gap-2">
        <a :href="release.htmlUrl" target="_blank">
          <i class="fab fa-github"></i>
        </a>
        <h6 class="mb-0 fw-bold">{{ release.name || release.tagName }}</h6>
        <span v-if="release.createdByIntegration" class="badge bg-secondary"
          ><i class="fas fa-download"></i> Created by integration</span
        >
      </div>
      <div class="d-flex align-items-center gap-2">
        <span v-if="release.importedSyncState?.status" class="badge" :class="statusBadgeClass">{{
          statusLabel
        }}</span>
        <BootstrapTooltip
          v-if="release.importedSyncState?.status === 'ERROR' && errorMessage"
          :title="errorMessage"
          icon-class="fas fa-exclamation-triangle text-danger"
          placement="bottom"
        />
        <button
          v-if="release.importedSyncState?.canReimport && release.importedSyncState?.status"
          class="btn btn-link btn-sm"
          :disabled="isImporting"
          title="Retry import"
          @click="handleImport"
        >
          <i v-if="!isImporting" class="fas fa-redo"></i>
          <span
            v-else
            class="spinner-border spinner-border-sm"
            role="status"
            aria-hidden="true"
          ></span>
        </button>
        <button
          v-else-if="!release.createdByIntegration"
          class="btn btn-primary btn-sm"
          :disabled="isImporting"
          @click="handleImport"
        >
          <span
            v-if="isImporting"
            class="spinner-border spinner-border-sm me-2"
            role="status"
            aria-hidden="true"
          ></span>
          <i v-else class="fas fa-download me-1"></i>
          Import
        </button>
      </div>
    </div>

    <div class="d-flex align-items-center gap-2 text-muted small">
      <span>Released {{ (release.publishedAt || release.createdAt)?.split("T")[0] }}</span>
    </div>

    <BootstrapModal id="versionModal" title="Specify Version" ref="versionModal" centered>
      <template #body>
        <p class="text-muted mb-3">
          This release does not conform to semantic versioning. Please specify a version number.
        </p>
        <div class="mb-3">
          <label for="custom-version" class="form-label">Version Number</label>
          <input
            id="custom-version"
            type="text"
            class="form-control"
            placeholder="e.g., 1.0.0"
            v-model="customVersion"
          />
        </div>
      </template>
      <template #footer>
        <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!customVersion.trim()"
          @click="handleVersionSubmit"
        >
          Pull Release
        </button>
      </template>
    </BootstrapModal>
  </li>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import type { GitHubRelease } from "@/types";
import BootstrapModal from "@/components/BootstrapModal.vue";
import BootstrapTooltip from "@/components/BootstrapTooltip.vue";

export interface GitHubReleaseItemProps {
  release: GitHubRelease;
  codebaseIdentifier: string;
}

const props = defineProps<GitHubReleaseItemProps>();

const emit = defineEmits<{
  "import-started": [release: GitHubReleaseItemProps["release"]];
}>();

const isImporting = ref(false);
const versionModal = ref();
const customVersion = ref("");

const { importGitHubRelease } = useGitRemotesAPI(props.codebaseIdentifier);

const statusLabel = computed(() => {
  const state = props.release.importedSyncState;
  if (!state) return "";
  switch (state.status) {
    case "SUCCESS":
      return "Success";
    case "RUNNING":
      return "In Progress";
    case "ERROR":
      return "Failed";
    default:
      return null;
  }
});

const statusBadgeClass = computed(() => {
  const state = props.release.importedSyncState;
  if (!state) return null;
  switch (state.status) {
    case "SUCCESS":
      return "bg-success";
    case "RUNNING":
      return "bg-warning";
    case "ERROR":
      return "bg-danger";
    default:
      return null;
  }
});

const errorMessage = computed(() => props.release.importedSyncState?.errorMessage || "");

const handleImport = async () => {
  if (!props.release.hasSemanticVersioning) {
    customVersion.value = "";
    versionModal.value?.show();
    return;
  }
  await importRelease();
};

async function importRelease(version?: string) {
  isImporting.value = true;
  try {
    await importGitHubRelease(props.release.id, version);
    emit("import-started", props.release);
  } finally {
    isImporting.value = false;
  }
}

async function handleVersionSubmit() {
  if (!customVersion.value.trim()) return;
  await importRelease(customVersion.value);
  versionModal.value?.hide();
  customVersion.value = "";
}
</script>
