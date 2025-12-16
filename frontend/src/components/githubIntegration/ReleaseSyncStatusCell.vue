<template>
  <div class="d-flex flex-column align-items-center gap-1">
    <div v-if="isPendingImport" class="d-flex align-items-center gap-2">
      <button class="btn btn-primary btn-sm" @click="handleImportClick">
        <i class="fas fa-arrow-left me-2"></i>
        Import
      </button>
    </div>

    <div v-else-if="hasStatus" class="d-flex flex-column align-items-center gap-1">
      <div class="d-inline-flex align-items-center">
        <span v-if="direction === 'left'" :class="arrowClass"
          ><i class="fas fa-arrow-left"></i
        ></span>
        <span class="badge" :class="badgeClass">
          <i class="fas fa-spinner fa-spin" v-if="currentStatus === 'RUNNING'"></i>
          {{ badgeText }}
        </span>
        <span v-if="direction === 'right'" :class="arrowClass"
          ><i class="fas fa-arrow-right"></i
        ></span>
        <BootstrapTooltip
          class="ms-1"
          :title="errorMessage"
          v-if="currentStatus === 'ERROR' && errorMessage"
          icon-class="fas fa-info-circle text-muted"
          placement="bottom"
        ></BootstrapTooltip>
      </div>
      <small v-if="metadataPending" class="text-muted">
        update pending
        <BootstrapTooltip
          title="The release was updated since it was last pushed to GitHub, these changes will be pushed along with any pending releases, though this won't apply to the main branch unless this is the latest release."
          icon-class="fas fa-question-circle text-muted"
          placement="bottom"
        ></BootstrapTooltip>
      </small>
      <button v-if="showRetryImport" class="btn btn-link btn-sm p-0" @click="handleImportClick">
        <i class="fas fa-redo me-1"></i>
        Retry
      </button>
      <button v-else-if="showReimport" class="btn btn-link btn-sm p-0" @click="handleImportClick">
        <i class="fas fa-redo me-1"></i>
        Reimport
      </button>
    </div>

    <div v-else style="min-height: 1.5rem"></div>

    <BootstrapModal
      v-if="entry.githubRelease"
      :id="`versionModal-${entry.githubRelease.id}`"
      title="Specify Version"
      ref="versionModal"
      centered
    >
      <template #body>
        <p class="text-muted mb-3">
          This release does not conform to semantic versioning. Please specify a version number.
        </p>
        <div class="mb-3">
          <label for="custom-version" class="form-label">Version Number</label>
          <input
            :id="`custom-version-${entry.githubRelease.id}`"
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
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import BootstrapModal from "@/components/BootstrapModal.vue";
import BootstrapTooltip from "@/components/BootstrapTooltip.vue";
import type { ReleaseAlignment, GitRefSyncState, ImportedReleaseSyncState } from "@/types";

const props = defineProps<{
  entry: ReleaseAlignment[string];
}>();

const emit = defineEmits<{
  "run-import": [ReleaseAlignment[string], string?];
}>();

const localState = computed(
  () => props.entry.localRelease?.gitRefSyncState as GitRefSyncState | undefined
);
const importState = computed(
  () => props.entry.githubRelease?.importedSyncState as ImportedReleaseSyncState | undefined
);

const direction = computed<"left" | "right" | null>(() => {
  if (localState.value) return "right";
  if (importState.value) return "left";
  return null;
});

const currentStatus = computed(() => localState.value?.status || importState.value?.status || null);
const hasStatus = computed(() => Boolean(currentStatus.value));
const badgeText = computed(() => {
  if (!currentStatus.value) return "";
  if (currentStatus.value === "SUCCESS") return direction.value === "right" ? "Pushed" : "Imported";
  if (currentStatus.value === "RUNNING")
    return direction.value === "right" ? "Pushing" : "Importing";
  if (currentStatus.value === "ERROR") return "Failed";
  return "Pending";
});
const badgeColor = computed(() => statusBadgeColor(currentStatus.value));
const badgeClass = computed(() => `bg-${badgeColor.value}`);
const arrowClass = computed(() => `text-${badgeColor.value}`);

const errorMessage = computed(
  () => localState.value?.errorMessage || importState.value?.errorMessage || null
);
const isPendingImport = computed(() => {
  const imp = importState.value;
  return Boolean(imp && imp.status === "PENDING");
});

const metadataPending = computed(() => {
  return (
    direction.value === "right" &&
    currentStatus.value === "SUCCESS" &&
    localState.value?.canPush === true
  );
});

const showRetryImport = computed(() => {
  return direction.value === "left" && currentStatus.value === "ERROR";
});

const showReimport = computed(() => {
  const gh = props.entry.githubRelease;
  const local = props.entry.localRelease;
  return (
    direction.value === "left" &&
    currentStatus.value === "SUCCESS" &&
    gh?.importedSyncState?.canReimport &&
    local &&
    local.live === false
  );
});
const customVersion = ref("");
const versionModal = ref<any>(null);

function handleImportClick() {
  const release = props.entry.githubRelease;
  if (!release) return;
  const local = props.entry.localRelease;

  if (!release.hasSemanticVersioning && local?.versionNumber) {
    emit("run-import", props.entry, local.versionNumber);
    return;
  }
  if (!release.hasSemanticVersioning) {
    customVersion.value = "";
    showVersionModal();
    return;
  }
  emit("run-import", props.entry);
}

function handleVersionSubmit() {
  const release = props.entry.githubRelease;
  if (!release) return;
  const version = customVersion.value.trim();
  if (!version) return;
  emit("run-import", props.entry, version);
  customVersion.value = "";
  hideVersionModal();
}

function showVersionModal() {
  versionModal.value?.show();
}

function hideVersionModal() {
  versionModal.value?.hide();
}

function statusBadgeColor(status?: string | null) {
  switch (status) {
    case "SUCCESS":
      return "success";
    case "RUNNING":
      return "warning";
    case "ERROR":
      return "danger";
    case "PENDING":
    default:
      return "gray";
  }
}
</script>
