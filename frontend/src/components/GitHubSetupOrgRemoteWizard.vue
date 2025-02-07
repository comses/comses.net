<template>
  <div class="card bg-light">
    <button class="btn btn-link ps-0" @click="show = !show">
      <i v-if="show" class="fas fa-minus"></i>
      <i v-else class="fas fa-plus"></i>
      Create a new repository
    </button>
    <div v-if="show" class="card-body">
      <label for="repo-name" class="form-label">Choose a repository name</label>
      <div class="input-group">
        <span class="input-group-text"><i class="fab fa-github me-1"></i>{{ owner }}/</span>
        <input
          type="text"
          class="form-control"
          placeholder="repository name"
          v-model="repoName"
          id="repo-name"
        />
      </div>
      <div class="form-text mb-3">
        The name can only contain letters, digits, and the characters ., -, and _
      </div>
      <button class="btn btn-primary" type="button" @click="setupRemote" :disabled="isLoading">
        Create repository and push releases
      </button>
      <div v-if="isLoading" class="text-muted text-center p-3">
        <i class="fas fa-spinner fa-spin"></i>
      </div>
      <FormAlert
        v-if="serverErrors.length > 0"
        :validation-errors="[]"
        :server-errors="serverErrors"
      />
      <div
        v-else-if="successMessage"
        class="alert alert-success alert-dismissible fade show mb-0 mt-3"
      >
        {{ successMessage }}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import FormAlert from "@/components/form/FormAlert.vue";

const props = defineProps<{
  codebaseIdentifier: string;
  owner: string;
  defaultRepoName: string;
}>();

const emit = defineEmits<{
  success: [];
}>();

const { isLoading, serverErrors, setupOrgGithubRemote } = useGitRemotesAPI(
  props.codebaseIdentifier
);
const successMessage = ref<string | null>(null);
const repoName = ref(props.defaultRepoName);

const show = ref(false);

const setupRemote = async () => {
  const onSuccess = () => {
    successMessage.value =
      "Sync in progress. Refresh this page in a few seconds to check the status.";
    emit("success");
  };
  await setupOrgGithubRemote(repoName.value, { onSuccess });
};
</script>
