<template>
  <div>
    <div class="input-group mb-3">
      <span class="input-group-text"><i class="fab fa-github me-1"></i>{{ owner }}/</span>
      <input type="text" class="form-control" placeholder="repository name" v-model="repoName" />
    </div>
    <button class="btn btn-primary" type="button" @click="setupRemote" :disabled="isLoading">
      Create
    </button>
    <div v-if="isLoading" class="text-muted text-center p-3">
      <i class="fas fa-spinner fa-spin"></i>
    </div>
    <FormAlert v-if="serverErrors" :validation-errors="[]" :server-errors="serverErrors" />
    <div
      v-else-if="successMessage"
      class="alert alert-success alert-dismissible fade show mb-0 mt-3"
    >
      {{ successMessage }}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import FormAlert from "@/components/form/FormAlert.vue";

const props = defineProps<{
  codebaseIdentifier: string;
  isUserRepo: boolean;
  owner: string;
  defaultRepoName: string;
}>();

const emit = defineEmits<{
  success: [];
}>();

const { isLoading, serverErrors, setupOrgGithubRemote, setupUserGithubRemote } = useGitRemotesAPI(
  props.codebaseIdentifier
);
const successMessage = ref<string | null>(null);
const repoName = ref(props.defaultRepoName);

const setupRemote = async () => {
  const onSuccess = () => {
    successMessage.value =
      "Sync in progress. Refresh this page in a few seconds to check the status.";
    emit("success");
  };
  if (props.isUserRepo) {
    await setupUserGithubRemote(repoName.value, { onSuccess });
  } else {
    await setupOrgGithubRemote(repoName.value, { onSuccess });
  }
};
</script>
