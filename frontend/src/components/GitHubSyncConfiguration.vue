<template>
  <div style="min-height: 60vh">
    <div class="row mb-5">
      <div class="col-12 col-md-4 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="fw-bold">When syncing with a new GitHub repository...</h5>
            <p class="card-text">
              A git repo will be automatically built from the public releases of your model and
              pushed to GitHub.
            </p>
            <p class="card-text">
              <strong>Pushing</strong> and <strong>Importing</strong> will be enabled*, meaning new
              releases published on CoMSES will be pushed to the GitHub repo and vice-versa
            </p>
          </div>
        </div>
      </div>
      <div class="col-12 col-md-4 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="fw-bold">When syncing with an existing repository...</h5>
            <p class="card-text">
              <strong>Importing</strong> will be enabled*, meaning new releases published on the
              synced GitHub repository will be automatically pulled back into the CoMSES Model
              Library.
            </p>
            <p class="card-text">This works similarly to the <em>Zenodo</em> GitHub integration.</p>
          </div>
        </div>
      </div>
      <div class="col-12 col-md-4 mb-3">
        <GitHubInstallationStatus :installation-status="installationStatus" class="h-100" />
      </div>
      <div class="col-12 text-muted">
        <small
          >* Pushing and importing can be enabled or disabled independently to control the sync
          direction.</small
        >
      </div>
    </div>
    <div class="d-flex justify-content-between align-items-end mb-3">
      <div>
        <h3>Repositories linked with this model</h3>
        <p class="text-muted mb-0 pe-5">
          Only one linked repository can be active at a time. A repository is considered active if
          either pushing or importing is turned on.
        </p>
      </div>
      <button
        class="btn btn-primary flex-shrink-0"
        @click="openSetupModal"
        :disabled="!canSetupSync"
      >
        <i class="fas fa-plus me-2"></i>
        Sync with a repository
      </button>
    </div>
    <div class="card mb-3">
      <div class="card-header">
        <ul class="nav nav-tabs card-header-tabs">
          <li class="nav-item">
            <a
              class="nav-link"
              :class="{ active: selectedUserTab === 'active' }"
              @click="selectedUserTab = 'active'"
              >Active</a
            >
          </li>
          <a
            class="nav-link"
            :class="{ active: selectedUserTab === 'inactive' }"
            @click="selectedUserTab = 'inactive'"
            >Inactive</a
          >
        </ul>
      </div>
      <ol class="list-group list-group-flush">
        <li v-if="remotesLoading" class="list-group-item text-muted text-center p-3">
          <i class="fas fa-spinner fa-spin"></i>
        </li>
        <li v-else-if="userRemotes.length === 0" class="list-group-item text-muted">
          No {{ selectedUserTab }} repos.
        </li>
        <li v-else v-for="remote in userRemotes" :key="remote.id" class="list-group-item">
          <GitHubRemoteItem
            :codebase-identifier="codebaseIdentifier"
            :remote="remote"
            @changed="fetchRemotes"
          />
        </li>
      </ol>
    </div>

    <p class="text-muted" v-if="!isCodebaseLive">
      <small>* Must have at least one published release to generate a new repository. </small>
    </p>

    <BootstrapModal id="github-setup-modal" size="lg" centered ref="setupModal">
      <template #body>
        <GitHubSetupUserRemoteWizard
          :codebase-identifier="codebaseIdentifier"
          :default-repo-name="defaultRepoName"
          :installation-status="installationStatus"
          :disabled="!isCodebaseLive"
          @success="handleSetupSuccess"
        />
      </template>
      <template #footer>
        <div class="w-100 d-flex justify-content-between">
          <div class="mt-3">
            <small class="text-muted">
              <i class="fas fa-question-circle"></i> Need help? Check the
              <a href="/github/#faq" target="_blank">GitHub Sync FAQ</a>
            </small>
          </div>
          <button class="btn btn-outline-gray" @click="setupModal.hide()">Close</button>
        </div>
      </template>
    </BootstrapModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import type { GitHubAppInstallationStatus, CodebaseGitRemote } from "@/types";
import GitHubRemoteItem from "@/components/GitHubRemoteItem.vue";
import GitHubSetupUserRemoteWizard from "@/components/GitHubSetupUserRemoteWizard.vue";
import GitHubInstallationStatus from "@/components/GitHubInstallationStatus.vue";
import BootstrapModal from "@/components/BootstrapModal.vue";

const props = defineProps<{
  codebaseIdentifier: string;
  githubOrgName: string;
  defaultRepoName: string;
  isCodebaseLive: boolean;
}>();

const { list, getSubmitterInstallationStatus } = useGitRemotesAPI(props.codebaseIdentifier);

const installationStatus = ref<GitHubAppInstallationStatus>({
  githubAccount: null,
  installationUrl: null,
  connectUrl: "",
});

const remotesLoading = ref(true);
const remotes = ref<CodebaseGitRemote[]>([]);
const activeUserRemotes = computed(() => remotes.value.filter(r => r.isUserRepo && r.isActive));
const inactiveUserRemotes = computed(() => remotes.value.filter(r => r.isUserRepo && !r.isActive));
const setupModal = ref();

const selectedUserTab = ref<"active" | "inactive">("active");
const userRemotes = computed(() => {
  if (selectedUserTab.value === "inactive") {
    return inactiveUserRemotes.value;
  } else {
    return activeUserRemotes.value;
  }
});

const canSetupSync = computed(() => {
  return installationStatus.value.githubAccount?.installationId && props.isCodebaseLive;
});

const fetchRemotes = async () => {
  remotesLoading.value = true;
  remotes.value = (await list()).data;
  remotesLoading.value = false;
};

const openSetupModal = () => {
  setupModal.value?.show();
};

const handleSetupSuccess = () => {
  fetchRemotes();
};

onMounted(async () => {
  installationStatus.value = (await getSubmitterInstallationStatus()).data;
  await fetchRemotes();
});
</script>
