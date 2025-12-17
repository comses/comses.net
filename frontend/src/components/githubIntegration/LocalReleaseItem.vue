<template>
  <li class="list-group-item p-2 rounded" :class="itemClass">
    <div class="d-flex flex-column gap-1">
      <div class="d-flex align-items-center gap-2">
        <a :href="release.absoluteUrl" target="_blank"><i class="fas fa-link"></i></a>
        <h6 class="mb-0 fw-bold d-flex align-items-center gap-2">
          <span>v{{ release.versionNumber }}</span>
          <span v-if="!release.live" class="badge bg-gray">
            <i class="fas fa-lock"></i> Private
          </span>
        </h6>
        <span v-if="release.status.toLowerCase() === 'under_review'" class="badge bg-danger"
          >Under Review</span
        >
      </div>
      <div class="text-muted small">
        <span v-if="!release.live">
          <span class="float-end">
            <a :href="editHref">
              <span v-if="release.reviewStatus?.toLowerCase() === 'awaiting_author_changes'">
                <i class="fas fa-bell"></i> Verify import and notify reviewers
              </span>
              <span v-else-if="release.importedReleaseSyncState"
                ><i class="fas fa-edit"></i> Verify import</span
              >
            </a>
            <BootstrapTooltip
              v-if="release.importedReleaseSyncState"
              class="ms-1"
              :title="tooltipTitle"
              icon-class="fas fa-question-circle text-muted"
              placement="bottom"
            >
            </BootstrapTooltip>
            <span v-else class="small">Only published releases are included in git repos</span>
          </span>
        </span>
        <span v-else>Published {{ release.lastPublishedOn }}</span>
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

const editHref = computed(() =>
  editUrl(props.release.codebase.identifier, props.release.versionNumber)
);

const tooltipTitle = computed(() => {
  if (props.release.status.toLowerCase() === "under_review") {
    return "Releases being reviewed must remain unpublished until complete. If revisions are requested, you will need to update the GitHub release tag (see tutorial for help), reimport, and then notify reviewers.";
  }
  return "Releases imported from GitHub will be unpublished until you verify and correct metadata and file categorization. Afterwards, you can publish OR request peer review.";
});

const isOriginal = computed(() => !props.release.importedReleaseSyncState);
const itemClass = computed(() => {
  return [
    { "opacity-50": !props.release.live && isOriginal.value },
    { "bg-blue-gray": isOriginal.value },
    { border: !isOriginal.value },
  ];
});
</script>
