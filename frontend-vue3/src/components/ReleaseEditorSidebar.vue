<template>
  <div>
    <nav class="nav flex-md-column">
      <router-link
        v-if="!isLive"
        to="/upload"
        class="card text-decoration-none flex-grow-1 mb-3 me-3 me-md-0"
        active-class="border-secondary"
      >
        <div
          class="card-header nav-link d-flex justify-content-between align-items-center text-decoration-none"
        >
          <b>Upload Files</b>
          <i class="fas fa-angle-right text-secondary"></i>
        </div>
        <div class="card-body pb-2 text-dark">
          <ReleaseEditorProgressCheck :check="uploadProgress.code" label="Code" />
          <ReleaseEditorProgressCheck :check="uploadProgress.docs" label="Documentation" />
          <ReleaseEditorProgressCheck :check="uploadProgress.data" label="Input Data" optional />
          <ReleaseEditorProgressCheck :check="uploadProgress.results" label="Results" optional />
        </div>
      </router-link>
      <router-link
        to="/metadata"
        class="card text-decoration-none flex-grow-1 mb-3 me-3 me-md-0"
        active-class="border-secondary"
      >
        <div
          class="card-header nav-link d-flex justify-content-between align-items-center text-decoration-none"
        >
          <b>Add Metadata</b>
          <i class="fas fa-angle-right text-secondary"></i>
        </div>
        <div class="card-body pb-2 text-dark">
          <ReleaseEditorProgressCheck :check="metadataProgress.notes" label="Release Notes" />
          <ReleaseEditorProgressCheck :check="metadataProgress.os" label="Operating System" />
          <ReleaseEditorProgressCheck :check="metadataProgress.platforms" label="Platform" />
          <ReleaseEditorProgressCheck :check="metadataProgress.languages" label="Language" />
          <ReleaseEditorProgressCheck :check="metadataProgress.license" label="License" />
        </div>
      </router-link>
      <router-link
        to="/contributors"
        class="card text-decoration-none flex-grow-1 mb-3 me-3 me-md-0"
        active-class="border-secondary"
      >
        <div
          class="card-header nav-link d-flex justify-content-between align-items-center text-decoration-none"
        >
          <b>Add Contributors</b>
          <i class="fas fa-angle-right text-secondary"></i>
        </div>
        <div class="card-body pb-2 text-dark">
          <ReleaseEditorProgressCheck :check="numContributors > 0">
            <template #label>
              {{ `${numContributors} Contributor${numContributors > 1 ? "s" : ""}` }}
            </template>
          </ReleaseEditorProgressCheck>
        </div>
      </router-link>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import ReleaseEditorProgressCheck from "@/components/ReleaseEditorProgressCheck.vue";

const props = defineProps<{
  isLive: boolean;
}>();

const store = useReleaseEditorStore();

const uploadProgress = computed(() => {
  const files = store.files.originals;
  return {
    code: files.code.length > 0,
    docs: files.docs.length > 0,
    data: files.data.length > 0,
    results: files.results.length > 0,
  };
});

const metadataProgress = computed(() => {
  const metadata = store.metadata;
  return {
    notes: !!metadata.release_notes,
    os: !!metadata.os.length,
    platforms: metadata.platforms.length > 0,
    languages: metadata.programming_languages.length > 0,
    license: !!metadata.license,
  };
});

const numContributors = computed(() => {
  return store.release.release_contributors.length;
});
</script>

<style lang="scss">
.router-link-exact-active {
  .nav-link {
    background-color: var(--bs-secondary);
    color: var(--bs-white) !important;
  }
}
</style>
