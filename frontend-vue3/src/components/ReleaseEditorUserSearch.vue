<template>
  <div>
    <label for="user-search" class="form-label" aria-labelledby="user-search">
      {{ label }}
    </label>
    <VueMultiSelect
      id="user-search"
      :multiple="true"
      track-by="username"
      label="username"
      :custom-label="userDisplay"
      :placeholder="placeholder"
      :options="matchingUsers"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :clear-on-select="true"
      :options-limit="50"
      :limit="20"
      @search-change="fetchMatchingUsers"
      @select="handleSelect"
    >
      <template #caret="{ toggle }">
        <div class="multiselect__search-toggle">
          <i class="fas fa-search" @mousedown.prevent.stop="toggle" />
        </div>
      </template>
      <template #noOptions>No matching users found.</template>
    </VueMultiSelect>
    <small class="form-text text-muted" aria-describedby="user-search">
      {{ help }}
    </small>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useDebounceFn } from "@vueuse/core";
import { useProfileAPI } from "@/composables/api";

export interface UserSearchProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  label?: string;
  help?: string;
  placeholder?: string;
}

const props = withDefaults(defineProps<UserSearchProps>(), {
  label: "Search for an Existing User",
  help: "Skip entering contributor details by searching for users already in our system",
  placeholder: "",
});
const emit = defineEmits(["select"]);

const matchingUsers = ref<any[]>([]);
const isLoading = ref(false);

const { search } = useProfileAPI();

const fetchMatchingUsers = useDebounceFn(async (query: string) => {
  if (query) {
    isLoading.value = true;
    const response = await search({ query });
    matchingUsers.value = response.data.results;
    isLoading.value = false;
  }
}, 600);

function userDisplay(user: any) {
  let displayName: string = user.name;
  if (user.name !== user.username) {
    displayName = `${user.name} (${user.username})`;
  }
  return `${displayName}${user.institution_name ? `, ${user.institution_name}` : ""}`;
}

function handleSelect(user: any) {
  emit("select", user);
}
</script>
