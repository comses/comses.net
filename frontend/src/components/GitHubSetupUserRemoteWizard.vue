<template>
  <div class="card bg-light">
    <button class="btn btn-link ps-0" @click="show = !show">
      <i v-if="show" class="fas fa-minus"></i>
      <i v-else class="fas fa-plus"></i>
      <span v-if="fromExisting"> Sync with an <b>existing</b> repository </span>
      <span v-else> Generate and sync with a <b>new</b> repository </span>
    </button>
    <div v-if="show" class="card-body">
      <ol class="mb-0">
        <li v-if="githubUsername" class="mb-2">
          Signed in as
          <a :href="`https://github.com/${githubUsername}`" target="_blank" class="badge bg-dark">
            <i class="fab fa-github"></i> {{ githubUsername }}
          </a>
          <i class="fas fa-check text-success ms-2"></i>
        </li>
        <li v-else class="mb-2">
          <a class="btn btn-link p-0" :href="installationStatus.connectUrl">
            <i class="fas fa-link"></i> Connect your GitHub account with CoMSES Net
          </a>
        </li>
        <li v-if="!fromExisting" class="mb-2">
          <div>
            <a
              class="btn btn-link p-0"
              :class="{ disabled: !githubUsername }"
              :href="newRepositoryUrl"
              target="_blank"
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
            <a
              class="btn btn-link p-0"
              :class="{ disabled: !githubUsername }"
              :href="installationStatus.installationUrl ?? ''"
              target="_blank"
            >
              <span v-if="githubAppInstalled"
                >Ensure the Sync app has access to the repository</span
              >
              <span v-else>Install the Sync app on your GitHub account</span>
            </a>
          </div>
          <small class="text-muted">
            <small>
              The app needs admin permissions for synced repos, you can restrict access by choosing
              "Only select repositories" and selecting the repo you want to sync
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
              <span v-if="fromExisting">Setup release importing</span>
              <span v-else>Push releases and setup importing</span>
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
      <div v-if="githubUsername" class="mt-3">
        <small class="text-muted">
          <small>
            <i class="fas fa-question-circle"></i> Need help? Check the
            <a href="/github/#faq" target="_blank">GitHub Sync FAQ</a>
          </small>
        </small>
      </div>
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
const repoName = ref("");

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
