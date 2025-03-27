<template>
  <div>
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
          </div>
        </template>
        <template v-else>
          <FileTree :directory="content" :categorizable="categorizable" />
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
}

const props = withDefaults(defineProps<FileTreeProps>(), {
  categorizable: false,
});

const { updateFileCategory } = useReleaseEditorAPI();

const store = useReleaseEditorStore();

const availableCategories = ref<FileCategory[]>(["code", "data", "metadata", "docs", "results"]);

function isFile(item: File | Folder): item is File {
  return !("contents" in item);
}

async function handleUpdateFileCategory(file: File, newCategory: string) {
  file.pendingCategory = newCategory as FileCategory;
  if (props.categorizable) {
    const response = await updateFileCategory(
      store.identifier,
      store.versionNumber,
      file.category, // old category
      file.path,
      newCategory
    );
    if (response.status === 200) {
      // refresh the original files list (determines the green check/red x in sidebar)
      for (const cat of [file.pendingCategory, file.category]) {
        await store.fetchOriginalFiles(cat);
      }
      file.category = newCategory as FileCategory;
    } else {
      console.error("Failed to update file category", response);
    }
    file.pendingCategory = undefined; // reset pending state
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
