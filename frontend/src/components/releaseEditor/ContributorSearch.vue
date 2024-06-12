<template>
  <div>
    <label for="user-search" class="form-label" aria-labelledby="user-search">
      {{ label }}
    </label>
    <VueMultiSelect
      id="existing-contributor-search"
      v-model="candidateContributor"
      label="familyName"
      track-by="id"
      placeholder="Find a contributor previously entered in our system"
      :allow-empty="true"
      :options="matchingContributors"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :options-limit="50"
      :limit="20"
      @search-change="fetchMatchingContributors"
      @select="handleSelect"
    >
      <template #caret="{ toggle }">
        <div class="multiselect__search-toggle">
          <i class="fas fa-search" @mousedown.prevent.stop="toggle" />
        </div>
      </template>
      <template #option="{ option }">
        <b>{{ contributorName(option) }}</b>
        <small class="text-muted">{{ contributorEmail(option) }}</small>
        <small>{{ contributorAffiliation(option) }}</small>
      </template>
      <template #singleLabel="{ option }">
        <b>{{ contributorName(option) }}</b>
        <small class="text-muted">{{ contributorEmail(option) }}</small>
        <small>{{ contributorAffiliation(option) }}</small>
      </template>
      <template #noOptions>No matching users found.</template>
    </VueMultiSelect>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useDebounceFn } from "@vueuse/core";
import { useContributorAPI } from "@/composables/api";
import type { Contributor } from "@/types";

export interface UserSearchProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  label?: string;
  placeholder?: string;
}

const props = withDefaults(defineProps<UserSearchProps>(), {
  label: "Search for Existing Contributors",
  placeholder: "",
});
const emit = defineEmits(["select"]);

const candidateContributor = ref<Contributor | null>(null);
const matchingContributors = ref<any[]>([]);
const isLoading = ref(false);

const { search } = useContributorAPI();

const fetchMatchingContributors = useDebounceFn(async (query: string) => {
  if (query) {
    isLoading.value = true;
    try {
      const response = await search({ query });
      matchingContributors.value = response.data.results;
    } catch (e) {
      // no-op
    } finally {
      isLoading.value = false;
    }
  }
}, 600);

function contributorName(contributor: Contributor) {
  if (contributor.user) {
    return contributor.user.memberProfile.name;
  } else {
    return contributor.name;
  }
}

function contributorEmail(contributor: Contributor) {
  let email = "";
  if (contributor.user) {
    email = contributor.user.memberProfile.email;
  } else {
    email = contributor.email || "";
  }
  return email ? ` (${email})` : "";
}

function contributorAffiliation(contributor: Contributor) {
  let affiliation = "";
  if (contributor.primaryJsonAffiliationName) {
    affiliation = contributor.primaryJsonAffiliationName || "";
  } else if (contributor.user) {
    affiliation = contributor.user.memberProfile.primaryAffiliationName || "";
  }
  return affiliation ? `, ${affiliation}` : "";
}

function handleSelect(contributor: Contributor) {
  emit("select", contributor);
}

// Expose a reset method
function resetSelectField() {
  candidateContributor.value = null;
}

// Export the reset method
defineExpose({ resetSelectField });
</script>
