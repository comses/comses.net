<template>
  <div class="card bg-light">
    <button class="btn btn-link ps-0" @click="show = !show">
      <i v-if="show" class="fas fa-minus"></i>
      <i v-else class="fas fa-plus"></i>
      <span v-if="fromExisting"> Sync with an existing repository </span>
      <span v-else> Sync with a new repository </span>
    </button>
    <div v-if="show" class="card-body">
      <ol class="mb-0">
        <li v-if="githubUsername" class="text-decoration-line-through mb-2">
          Connect your GitHub account
        </li>
        <li v-else class="mb-2">
          <a class="btn btn-link p-0" :href="installationStatus.connectUrl">
            <i class="fas fa-link"></i> Connect your GitHub account
          </a>
        </li>
        <li v-if="githubAppInstalled" class="text-decoration-line-through mb-2">
          Install the Sync app on your GitHub account
        </li>
        <li v-else class="mb-2">
          <a
            class="btn btn-link p-0"
            :class="{ disabled: !installationStatus.installationUrl }"
            :href="installationStatus.installationUrl ?? ''"
          >
            <i class="fas fa-download"></i> Install the Sync app on your GitHub account
          </a>
        </li>
        <li v-if="!fromExisting" class="mb-2">
          <div>
            <a
              class="btn btn-link p-0"
              :class="{ disabled: !githubAppInstalled }"
              :href="newRepositoryUrl"
              >Create an empty repository with your desired name on GitHub</a
            >
          </div>
          <small class="text-muted">
            <small>
              <i class="fas fa-exclamation-triangle"></i> Do <b>not</b> initialize the repository
              with any files such as a README or license
            </small>
          </small>
        </li>
        <li class="mb-2">
          <div>
            <label v-if="fromExisting" :for="`user-repo-name-${fromExisting}`" class="form-label"
              >Enter the name of your repository</label
            >
            <label v-else :for="`user-repo-name-${fromExisting}`" class="form-label"
              >Enter the name of the repository you just created</label
            >
            <div class="input-group mb-3">
              <span class="input-group-text"
                ><i class="fab fa-github me-1"></i>{{ githubUsername }}/</span
              >
              <input
                type="text"
                class="form-control"
                placeholder="repository name"
                v-model="repoName"
                :id="`user-repo-name-${fromExisting}`"
              />
            </div>
            <button
              class="btn btn-primary"
              type="button"
              @click="setupRemote"
              :disabled="isLoading || !canCreateUserRemote"
            >
              <span v-if="fromExisting">Setup release archiving</span>
              <span v-else>Push releases and setup archiving</span>
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
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import FormAlert from "@/components/form/FormAlert.vue";
import { GitHubAppInstallationStatus } from "@/types";

const props = defineProps<{
  codebaseIdentifier: string;
  defaultRepoName: string;
  fromExisting: boolean;
  installationStatus: GitHubAppInstallationStatus;
}>();

const emit = defineEmits<{
  success: [];
}>();

const { isLoading, serverErrors, data, setupUserGithubRemote, setupUserExistingGithubRemote } =
  useGitRemotesAPI(props.codebaseIdentifier);
const successMessage = ref<string | null>(null);
const repoName = ref(props.defaultRepoName);

const show = ref(false);

const githubUsername = computed(() => props.installationStatus.githubAccount?.username);
const githubAppInstalled = computed(() => !!props.installationStatus.githubAccount?.installationId);
const canCreateUserRemote = computed(() => !!githubUsername.value && githubAppInstalled.value);

const newRepositoryUrl = computed(
  () => `https://github.com/new?owner=${githubUsername.value}&name=${repoName.value}`
);

const setupRemote = async () => {
  const onSuccess = () => {
    successMessage.value = data.value;
    emit("success");
  };
  if (props.fromExisting) {
    await setupUserExistingGithubRemote(repoName.value, { onSuccess });
  } else {
    await setupUserGithubRemote(repoName.value, { onSuccess });
  }
};
</script>
