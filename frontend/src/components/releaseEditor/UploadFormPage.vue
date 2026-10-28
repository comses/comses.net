<template>
  <div>
    <FileUpload
      v-if="editable"
      title="Upload model files"
      instructions=""
      accepted-file-types="*/*"
      :originals="[]"
      :upload-url="packageFilesUrl(store.identifier, store.versionNumber)"
      category="package"
      hide-file-list
      @upload-done="refreshFiles"
    />
    <ul v-if="editable" class="text-muted small mb-3">
      <li>
        Submitted tarballs or zip archives are unpacked. System files may be removed but the
        original directory structure will be preserved.
      </li>
      <li>
        All file types are currently accepted though files should be stored in open or plaintext
        formats.
      </li>
      <li>
        We reserve the right to curate and remove executables, binaries, or other inappropriate
        content.
      </li>
      <li>Submissions are required to have source code and documentation at a minimum.</li>
      <li>
        We'll try to automatically categorize submitted files, please review the categorization
        below.
      </li>
    </ul>
    <div v-if="editable" class="text-muted mb-3">
      <div
        class="category-tabs nav nav-pills flex-nowrap w-100 gap-2"
        role="tablist"
        aria-label="File category guidance"
      >
        <button
          v-for="(category, index) in categories"
          :id="`file-guidance-tab-${category.id}`"
          :key="category.id"
          type="button"
          class="nav-link border d-flex align-items-center justify-content-center gap-1"
          :class="{ active: activeCategory === category.id, 'text-muted': !category.required }"
          role="tab"
          :aria-label="`${category.title}${category.required ? ' (required)' : ''}`"
          :aria-selected="activeCategory === category.id"
          :aria-controls="`file-guidance-content-${category.id}`"
          :tabindex="activeCategory === category.id ? 0 : -1"
          :data-cy="`file-guidance-${category.id}`"
          @click="activeCategory = category.id"
          @keydown="handleGuidanceKeydown($event, index)"
        >
          <span :class="category.icon" aria-hidden="true"></span>
          <span>{{ category.label }}</span>
          <span class="far fa-question-circle category-help" aria-hidden="true"></span>
        </button>
      </div>
      <div
        v-for="category in categories"
        v-show="activeCategory === category.id"
        :id="`file-guidance-content-${category.id}`"
        :key="category.id"
        class="border rounded p-3 mt-2"
        role="tabpanel"
        :aria-labelledby="`file-guidance-tab-${category.id}`"
        tabindex="0"
      >
        <p class="mb-0 small">
          {{ category.instructions }}
          <strong v-if="category.importantInstructions">{{
            category.importantInstructions
          }}</strong>
        </p>
      </div>
    </div>
    <div class="card card-body bg-light mt-3">
      <h3 class="card-title">Current Archival Package Filesystem Layout</h3>
      <div v-if="serverErrors.length" class="alert alert-danger">{{ serverErrors.join(", ") }}</div>
      <span v-else-if="folderContents === null">Loading files...</span>
      <FileTree
        v-if="folderContents"
        :directory="folderContents"
        :categorizable="editable"
        :removable="editable"
        @files-changed="refreshFiles"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import FileUpload from "@/components/releaseEditor/FileUpload.vue";
import FileTree from "@/components/releaseEditor/FileTree.vue";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import { useReleaseEditorAPI } from "@/composables/api";
import type { FileCategory, Folder } from "@/types";

const store = useReleaseEditorStore();
const categories = [
  {
    id: "code",
    label: "Code",
    icon: "fas fa-code",
    title: "Source Code",
    required: true,
    instructions: `Include the source code (e.g., a NetLogo .nlogo file) and dependencies necessary for someone else to run the model.`,
  },
  {
    id: "docs",
    label: "Docs",
    icon: "fas fa-file-alt",
    title: "Narrative Documentation",
    required: true,
    instructions: `Upload narrative documentation that comprehensively describes your computational model. The ODD Protocol, although designed for individual based or agent based simulation models, may serve as a useful reference for properly describing your computational model. Effective narrative documentation includes equations, pseudocode, and flow diagrams. Documentation formats include Markdown, OpenDocument Text files (ODT), and PDF documents.`,
  },
  {
    id: "data",
    label: "Data",
    icon: "fas fa-database",
    title: "Input Data",
    required: false,
    instructions: `Upload any input datasets required by your source code. Use relative paths to reference input data files so the model can run when downloaded.`,
    importantInstructions: `There is a limit on file upload size so if your datasets are very large (over 1 GB), please consider using a trusted data repository like osf.io, figshare, or Zenodo to publish your data and include references to your data in your code via DOI or other permanent URL.`,
  },
  {
    id: "results",
    label: "Results",
    icon: "fas fa-chart-bar",
    title: "Simulation Outputs",
    required: false,
    instructions: `Upload simulation outputs associated with your computational model.`,
    importantInstructions: `There is a limit on file upload size so if your datasets are very large (over 1 GB), please consider using a trusted data repository like osf.io, figshare, or Zenodo to publish your data and include references to it in your code via DOI or other permanent URL.`,
  },
  {
    id: "metadata",
    label: "Metadata",
    icon: "fas fa-info-circle",
    title: "Metadata",
    required: false,
    instructions: `Metadata files help others properly identify, cite, and reuse code. We'll generate CITATION.cff, codemeta.json, and LICENSE files automatically from your release metadata when publishing.`,
  },
];

const activeCategory = ref("code");

function handleGuidanceKeydown(event: KeyboardEvent, index: number) {
  let nextIndex: number;
  switch (event.key) {
    case "ArrowRight":
      nextIndex = (index + 1) % categories.length;
      break;
    case "ArrowLeft":
      nextIndex = (index + categories.length - 1) % categories.length;
      break;
    case "Home":
      nextIndex = 0;
      break;
    case "End":
      nextIndex = categories.length - 1;
      break;
    default:
      return;
  }
  event.preventDefault();
  activeCategory.value = categories[nextIndex].id;
  const tab = event.currentTarget as HTMLButtonElement;
  tab.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[nextIndex]?.focus();
}

const editable = computed(() => store.release.canEditOriginals);
const folderContents = ref<Folder | null>(null);
const { data, serverErrors, downloadPreview, packageFilesUrl } = useReleaseEditorAPI();

async function refreshFiles() {
  await downloadPreview(store.identifier, store.versionNumber);
  if (!serverErrors.value.length && data.value) folderContents.value = data.value as Folder;
  if (editable.value) {
    await Promise.all(
      (["code", "docs", "data", "results"] as FileCategory[]).map(store.fetchOriginalFiles)
    );
  }
}

watch(
  () => store.isInitialized,
  initialized => {
    if (initialized) refreshFiles();
  },
  { immediate: true }
);
</script>

<style scoped>
.category-tabs {
  --bs-nav-link-color: var(--bs-gray-700);
  --bs-nav-link-hover-color: var(--bs-gray-900);
  --bs-nav-pills-link-active-bg: var(--bs-gray-200);
  --bs-nav-pills-link-active-color: var(--bs-gray-800);
}

.category-tabs .nav-link {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  padding-inline: 0.875rem;
  font-size: 0.875rem;
}

.category-help {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  font-size: 0.625rem;
}
</style>
