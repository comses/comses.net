<template>
  <div>
    <div v-if="serverErrors.length" class="alert alert-danger">{{ serverErrors.join(", ") }}</div>
    <div class="d-flex align-items-center pt-1">
      <i class="fas fa-folder-open me-2"></i>
      <span>{{ directory.label }}</span>
    </div>
    <div class="ms-2 ps-3 border-start border-4">
      <div v-for="content in directory.contents" :key="content.label">
        <template v-if="isFile(content)">
          <div class="d-flex align-items-center file-row py-1">
            <i :class="['me-2', getFileIcon(content.category)]"></i>
            <label class="flex-grow-1">{{ content.label }}</label>
            <i class="fas fa-spinner fa-spin text-muted" v-if="content.pendingCategory"></i>
            <select
              v-if="categorizable"
              :value="content.pendingCategory || content.category"
              :aria-label="`Category for ${content.path}`"
              :data-file-path="content.path"
              @change="
                handleUpdateFileCategory(content, ($event.target as HTMLSelectElement).value)
              "
              :disabled="!!content.pendingCategory"
              class="form-select form-select-sm w-auto"
              style="border: none; background-color: transparent"
            >
              <option v-for="cat in availableCategories" :key="cat" :value="cat">
                {{ cat }}
              </option>
            </select>
            <button
              v-if="removable"
              type="button"
              class="btn btn-sm btn-link text-danger ms-2"
              :aria-label="`Remove ${content.path}`"
              :disabled="isLoading"
              @click="removeFile(content)"
            >
              <i class="fas fa-trash-alt"></i>
            </button>
          </div>
        </template>
        <template v-else>
          <FileTree
            :directory="content"
            :categorizable="categorizable"
            :removable="removable"
            @files-changed="emit('filesChanged')"
          />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { Folder, File, FileCategory } from "@/types";
import { useReleaseEditorAPI } from "@/composables/api";
import { useReleaseEditorStore } from "@/stores/releaseEditor";

export interface FileTreeProps {
  directory: Folder;
  categorizable?: boolean;
  removable?: boolean;
}

const props = withDefaults(defineProps<FileTreeProps>(), {
  categorizable: false,
});

const emit = defineEmits<{ (event: "filesChanged"): void }>();
const { updateFileCategory, deleteFile, packageFileUrl, serverErrors, isLoading } =
  useReleaseEditorAPI();

async function removeFile(file: File) {
  if (!window.confirm(`Remove ${file.path}?`)) return;
  await deleteFile(packageFileUrl(store.identifier, store.versionNumber, file.path));
  if (!serverErrors.value.length) emit("filesChanged");
}

const store = useReleaseEditorStore();

const availableCategories = ref<FileCategory[]>(["code", "data", "metadata", "docs", "results"]);

function isFile(item: File | Folder): item is File {
  return !("contents" in item);
}

async function handleUpdateFileCategory(file: File, newCategory: string) {
  if (!props.categorizable) return;
  file.pendingCategory = newCategory as FileCategory;
  try {
    await updateFileCategory(
      store.identifier,
      store.versionNumber,
      file.category,
      file.path,
      newCategory
    );
    if (!serverErrors.value.length) {
      const previous = file.category;
      file.category = newCategory as FileCategory;
      await Promise.all([previous, file.category].map(store.fetchOriginalFiles));
    }
  } finally {
    file.pendingCategory = undefined;
  }
}

function getFileIcon(category: FileCategory) {
  switch (category) {
    case "code":
      return "fas fa-code text-secondary";
    case "data":
      return "fas fa-database text-danger";
    case "metadata":
      return "fas fa-info-circle text-gray";
    case "docs":
      return "fas fa-file-alt text-success";
    case "results":
      return "fas fa-chart-bar text-danger";
    default:
      return "fas fa-file";
  }
}
</script>

<style scoped lang="scss">
.file-row:hover {
  background-color: rgba(0, 0, 0, 0.05);
}
</style>
