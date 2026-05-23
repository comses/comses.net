<template>
  <div>
    <p v-if="store.release.canEditOriginals">
      A codebase release should ideally include the source code, documentation, input data and
      dependencies necessary for someone else to understand, replicate, or reuse the model. Please
      note the active filesystem layout used to organize your files. Uploaded source code are placed
      in <code>project-root/code/</code>, data files go in <code>project-root/data/</code>,
      documentation files go in <code>project-root/docs/</code>, and simulation outputs go in
      <code>project-root/results/</code>. If your source code references uploaded data files please
      consider using the relative path <code>../data/&lt;datafile&gt;</code> to access those data
      files. This will make it easier for others to download, run, and review your model.
    </p>
    <p v-else>
      The current filesystem layout of your published model is shown below. This release has already
      been published so files are no longer editable.
    </p>
    <div class="card card-body bg-light">
      <h3 class="card-title">Current Archival Package Filesystem Layout</h3>
      <span class="text-warning" v-if="folderContents === null">Loading download preview...</span>
      <div class="alert alert-danger" v-else-if="serverErrors.length">
        {{ serverErrors.join(", ") }}
      </div>
      <div v-if="folderContents">
        <FileTree :directory="folderContents" />
      </div>
    </div>
    <div v-if="store.release.canEditOriginals">
      <div v-for="config in configs" :key="config.uploadType">
        <FileUpload
          :accepted-file-types="config.acceptedFileTypes"
          :instructions="config.instructions"
          :originals="store.getFilesInCategory(config.uploadType)"
          :upload-url="uploadUrl(config.uploadType)"
          :title="config.title"
          :category="config.uploadType"
          @delete-file="handleDeleteFile(config.uploadType, $event)"
          @clear="handleClear(config.uploadType)"
          @upload-done="handleUploadDone(config.uploadType)"
        >
        </FileUpload>
        <hr />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import FileUpload from "@/components/releaseEditor/FileUpload.vue";
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

const { data, serverErrors, downloadPreview, listOriginalsFileUrl } = useReleaseEditorAPI();

function uploadUrl(category: FileCategory) {
  return listOriginalsFileUrl(store.identifier, store.versionNumber, category);
}

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

async function handleUploadDone(category: FileCategory) {
  await store.fetchOriginalFiles(category);
  return getDownloadPreview();
}

async function handleDeleteFile(category: FileCategory, path: string) {
  await store.deleteFile(category, path);
  return getDownloadPreview();
}

async function handleClear(category: FileCategory) {
  await store.clearCategory(category);
  return getDownloadPreview();
}

const configs: Config[] = [
  {
    uploadType: "code",
    acceptedFileTypes: "*/*",
    title: "Upload Source Code (required)",
    instructions: `Upload a single plaintext source code file (e.g., a NetLogo .nlogo file) or a tarball or zip archive of
            plaintext source code representing your codebase. Submitted archives are unpacked with all files within
            the archive extracted during the publishing process. System files may be removed but your archive's original
            directory structure will be preserved. All file types are currently accepted though files should be stored
            in open or plaintext formats. We reserve the right to curate and remove executables, binaries, or
            inappropriate content.`,
  },
  {
    uploadType: "docs",
    acceptedFileTypes: "*/*",
    title: "Upload Narrative Documentation (required)",
    instructions: `Upload narrative documentation that comprehensively describes your computational model. The ODD
            Protocol, although designed for individual based or agent based simulation models, may serve as a
            useful reference for properly describing your computational model. Effective narrative documentation includes equations, pseudocode, and flow diagrams. Only open plaintext formats are accepted and include
            Markdown, OpenDocument Text files (ODT), and PDF documents.`,
  },
  {
    uploadType: "data",
    acceptedFileTypes: "*/*",
    title: "Upload Data (optional)",
    instructions: `Upload any input datasets required by your source code. There is a limit on file upload size so if
            your datasets are very large (over 1 GB), please consider using a trusted data repository like osf.io,
            figshare, or Zenodo to publish your data and include references to your data in your code via DOI or other
            permanent URL. If a zip or tar archive is uploaded it will be automatically unpacked. Files should be in
            plaintext or other open data formats but all file types are currently accepted. Please note that data files
            uploaded here will be placed in a "<project-root>/data" directory so if you'd like for your source code to
            work immediately when another researcher downloads your codebase, your code may need to reference your input
            data files via a relative path "../data/<your-data-file>".`,
  },
  {
    uploadType: "results",
    acceptedFileTypes: "*/*",
    title: "Upload Simulation Outputs (optional)",
    instructions: `Upload simulation outputs associated with your computational model. There is a limit on file upload
    size so if your datasets are very large (over 1 GB), please consider using a trusted data repository like osf.io,
    figshare, or Zenodo to publish your data and include references to it in your code via DOI or other permanent URL.
    Data files should be in plain text or other open data formats.`,
  },
];
</script>
