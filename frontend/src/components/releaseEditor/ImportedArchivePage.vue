<template>
  <div>
    <p>
      Below is the current filesystem layout of the archival package as it was imported from GitHub.
      Note that metadata files (<code>CITATION.cff</code>, <code>codemeta.json</code>) are
      automatically updated to contain the most accurate information about the model release and
      reflect its location in the CoMSES Model Library.
    </p>
    <p>
      Please review the file tree to ensure that all necessary files are present and re-categorize
      files as necessary. At least one code and documentation file is required for publishing.
    </p>
    <p>
      If you do need to add, remove, or update any files, you can do so by
      <a target="_blank" :href="store.release.importedReleasePackage?.htmlUrl"
        >updating the source GitHub release</a
      >
      to point at a new tag with the desired changes, which will trigger a re-import of the release.
      This can only be done if the release is unpublished or under review, once it is published the
      file package is locked.
    </p>
    <div class="card card-body bg-light">
      <h3 class="card-title">Current Archival Package Filesystem Layout</h3>
      <span class="text-warning" v-if="folderContents === null">Loading download preview...</span>
      <div class="alert alert-danger" v-else-if="serverErrors.length">
        {{ serverErrors.join(", ") }}
      </div>
      <div v-if="folderContents">
        <FileTree :categorizable="!store.release.live" :directory="folderContents" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import FileTree from "@/components/releaseEditor/FileTree.vue";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import { useReleaseEditorAPI } from "@/composables/api";
import type { FileCategory, Folder } from "@/types";

export interface Config {
  uploadType: FileCategory;
  acceptedFileTypes: string;
  title: string;
  instructions: string;
}

const store = useReleaseEditorStore();

const folderContents = ref<Folder | null>(null);

const { data, serverErrors, downloadPreview } = useReleaseEditorAPI();

onMounted(() => {
  if (store.isInitialized) {
    getDownloadPreview();
  }
});

watch(
  () => store.isInitialized,
  () => {
    if (store.isInitialized) {
      getDownloadPreview();
    }
  }
);

async function getDownloadPreview() {
  await downloadPreview(store.identifier, store.versionNumber);
  if (serverErrors.value.length === 0 && data.value) {
    folderContents.value = data.value as Folder;
  }
}
</script>
