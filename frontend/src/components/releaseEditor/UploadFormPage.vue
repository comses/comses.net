<template>
  <div>
    <p>
      A codebase release should ideally include the source code, documentation, input data and
      dependencies necessary for someone else (including your future self) to understand, replicate,
      or reuse the model. Please note that we impose a specific directory structure to organize your
      uploaded files - you can view the active filesystem layout below. Source code is placed in
      <code>project-root/code/</code>, data files are placed in <code>project-root/data/</code>, and
      documentation files are placed in <code>project-root/docs/</code>, and simulation outputs are
      placed in <code>project-root/results/</code>. This means that if your source code has
      references to your uploaded data files you should consider using the relative path
      <code>../data/&lt;datafile&gt;</code> to access those data files. This will make the lives of
      others wishing to review, download and run your model easier.
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
    <div v-for="config in configs" :key="config.uploadType">
      <FileUpload
        :accepted-file-types="config.acceptedFileTypes"
        :instructions="config.instructions"
        :originals="store.getFilesInCategory(config.uploadType)"
        :upload-url="uploadUrl(config.uploadType)"
        :title="config.title"
        @delete-file="handleDeleteFile(config.uploadType, $event)"
        @clear="handleClear(config.uploadType)"
        @upload-done="handleUploadDone(config.uploadType)"
      >
      </FileUpload>
      <hr />
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
    instructions: `You can upload a single plaintext source file (e.g., a NetLogo .nlogo file) or a tar or zip archive of
            plaintext source code representing your codebase. Archives will be unpacked and extracted as part of archival processing
            and system files will be removed but the archive's directory structure is preserved.  All file types are currently
            accepted though files should be stored in open or plaintext formats. We may remove executables or binaries in the
            future.`,
  },
  {
    uploadType: "docs",
    acceptedFileTypes: "*/*",
    title: "Upload Narrative Documentation (required)",
    instructions: `Upload narrative documentation that comprehensively describes your computational model. The ODD
            Protocol offers a good starting point for thinking about how to comprehensively describe agent based models and
            good Narrative Documentation often includes equations, pseudocode, and flow diagrams. Acceptable files include
            plain text formats (including Markdown and other structured text), OpenDocument Text files (ODT), and PDF documents.`,
  },
  {
    uploadType: "data",
    acceptedFileTypes: "*/*",
    title: "Upload Data (optional)",
    instructions: `Upload any datasets required by your source code. There is a limit on file upload size so if
            your datasets are very large, you may consider using osf.io or figshare or other data repository to store your
            data and refer to it in your code via DOI or other permanent URL. If a zip or tar archive is uploaded
            it will be automatically unpacked. Files should be plaintext or an open data formats but all file types
            are currently accepted. Please note that data files uploaded here will be placed in a "<project-root>/data"
            directory so if you'd like for your source code to work immediately when another researcher downloads your
            codebase, please consider referring to any input data files via a relative path "../data/<your-data-file>".`,
  },
  {
    uploadType: "results",
    acceptedFileTypes: "*/*",
    title: "Upload Simulation Outputs (optional)",
    instructions:
      "Upload simulation outputs associated with your computational model. Ideally these data files should be in plain text or other open data formats.",
  },
];
</script>
