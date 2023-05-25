<template>
  <div>
    <div :style="indented">
      <i class="fas fa-folder-open"></i> {{ directory.label }}
      <div v-for="content in directory.contents" :key="content.label">
        <div v-if="isFile(content)" :style="indented">
          <i class="fas fa-file"></i> {{ content.label }}
        </div>
        <ReleaseEditorFileTree v-else :directory="(content as Folder)" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Folder, File } from "@/types";

const props = defineProps<{
  directory: Folder;
}>();

const indented = "transform: translate(50px)";

function isFile(contents: File | Folder) {
  return !("contents" in contents);
}
</script>
