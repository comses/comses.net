<template>
  <div>
    <div v-if="!githubIsSetup" class="alert alert-warning">
      <i class="fas fa-exclamation-triangle me-2"></i>
      Please ensure your GitHub account is connected and the CoMSES Net Sync app is installed using
      the status widget above.
    </div>
    <div v-else class="m-3">
      <div class="d-flex justify-content-center mb-5">
        <div class="btn-group border border-dark rounded-3 w-100" role="group">
          <button
            type="button"
            class="btn py-3 px-4 rounded-3 w-50"
            :class="!fromExisting ? 'btn-dark' : 'text-muted'"
            @click="fromExisting = false"
            :disabled="props.disabled"
          >
            <i class="fas fa-plus me-2"></i>
            <div>
              <strong class="d-block">Sync with a <u>new</u> repository</strong>
            </div>
          </button>
          <button
            type="button"
            class="btn py-3 px-4 rounded-3 w-50"
            :class="fromExisting ? 'btn-dark' : 'text-muted'"
            @click="fromExisting = true"
          >
            <i class="fab fa-github me-2"></i>
            <div>
              <strong class="d-block">Sync with an <u>existing</u> repository</strong>
            </div>
          </button>
        </div>
      </div>
      <div v-if="!fromExisting">
        <div class="mb-4 text-center">
          <p class="mb-2">
            First, create an empty repository on GitHub with a name of your choosing.
          </p>
          <small class="text-muted d-block mb-3">
            <i class="fas fa-exclamation-triangle me-1 text-danger"></i>
            <u>Do not</u> initialize the repository with any files such as a README, .gitignore, or
            license.
          </small>
          <a class="btn btn-secondary" :href="newRepositoryUrl" target="_blank">
            <i class="fab fa-github me-2"></i>
            Create GitHub repository
          </a>
        </div>

        <hr class="my-4" />
      </div>
      <div class="mb-4 text-center">
        <p class="mb-3">
          <span v-if="!fromExisting">Next,</span>
          <span v-else>First,</span>
          make sure the CoMSES Sync app has access to your repository.
        </p>
        <a
          class="btn btn-outline-secondary"
          :href="installationStatus.installationUrl || ''"
          target="_blank"
        >
          <i class="fas fa-cog me-2"></i>
          Configure app permissions
        </a>
      </div>
      <hr class="my-4" />
      <div class="text-center">
        <label for="user-repo-name" class="form-label">
          <span v-if="fromExisting">Enter the name of your existing repository</span>
          <span v-else>Finally, enter the name of the repository you just created</span>
        </label>
        <div class="input-group mb-3">
          <span class="input-group-text">
            <i class="fab fa-github me-1"></i>{{ githubUsername }}/
          </span>
          <input
            type="text"
            class="form-control"
            placeholder="repository name"
            v-model="repoName"
            id="user-repo-name"
          />
        </div>
        <button
          class="btn btn-primary"
          type="button"
          @click="setupRemote"
          :disabled="isLoading || !canProceed || !repoName.trim() || !!successMessage"
        >
          <span v-if="fromExisting">Setup Release Importing</span>
          <span v-else>Push Releases and Setup Importing</span>
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
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import FormAlert from "@/components/form/FormAlert.vue";
import type { GitHubAppInstallationStatus } from "@/types";

export interface GitHubSetupUserRemoteWizardProps {
  codebaseIdentifier: string;
  defaultRepoName: string;
  installationStatus: GitHubAppInstallationStatus;
  disabled: boolean;
}

const props = withDefaults(defineProps<GitHubSetupUserRemoteWizardProps>(), {
  disabled: false,
});

const emit = defineEmits<{
  success: [];
}>();

const { isLoading, serverErrors, data, setupUserGithubRemote, setupUserExistingGithubRemote } =
  useGitRemotesAPI(props.codebaseIdentifier);
const successMessage = ref<string | null>(null);
const repoName = ref("");
const fromExisting = ref(props.disabled);

const githubUsername = computed(() => props.installationStatus.githubAccount?.username);
const githubIsSetup = computed(() => !!props.installationStatus.githubAccount?.installationId);

const canProceed = computed(() => {
  if (!githubIsSetup.value) {
    return false;
  }
  if (fromExisting.value) {
    return true; // always allow for existing repos if github is setup
  }
  return !props.disabled; // for new repos, codebase must be live
});

const newRepositoryUrl = computed(
  () => `https://github.com/new?owner=${githubUsername.value}&name=${repoName.value}`
);

const setupRemote = async () => {
  const onSuccess = () => {
    successMessage.value = data.value;
    emit("success");
  };
  if (fromExisting.value) {
    await setupUserExistingGithubRemote(repoName.value, { onSuccess });
  } else {
    await setupUserGithubRemote(repoName.value, { onSuccess });
  }
};
</script>
