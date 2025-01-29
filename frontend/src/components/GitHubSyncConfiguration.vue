<template>
  <p>
    GitHub Sync allows you to connect your model in the CoMSES Model Library (CML) to a GitHub
    repository.
  </p>
  <p>
    When creating a new repository here, a git repo will be automatically built from the public
    releases of your model and <b><u>pushed</u></b> to GitHub. This will be updated every time you
    publish a new release or update the metadata of an existing one, until it is disabled.
  </p>
  <p>
    Changes made to synced repositories on GitHub can be automically pulled back into the CML by
    enabling the <b><u>archiving</u></b> feature and creating a new release on GitHub. This works
    similarly to the <i>Zenodo</i> GitHub integration.
  </p>
  <hr />
  <div class="row" style="min-height: 60vh">
    <div class="col border-end">
      <h3><i class="fas fa-university"></i> Repositories in the CoMSES organization</h3>
      <p>
        Synced repositories in the
        <a :href="`https://github.com/orgs/${githubOrgName}/repositories`"
          ><i class="fab fa-github"></i>{{ githubOrgName }}</a
        >
        organization are <b><u>push-only</u></b> since they are intended as a read-only mirror of
        your model submission on CoMSES. This is a good way to enhance the accessibility of your
        model's source code without a GitHub account.
      </p>
      <div class="card mb-3">
        <div class="card-header">
          <ul class="nav nav-tabs card-header-tabs">
            <li class="nav-item">
              <a
                class="nav-link"
                :class="{ active: selectedOrgTab === 'active' }"
                @click="selectedOrgTab = 'active'"
                >Active</a
              >
            </li>
            <a
              class="nav-link"
              :class="{ active: selectedOrgTab === 'inactive' }"
              @click="selectedOrgTab = 'inactive'"
              >Inactive</a
            >
          </ul>
        </div>
        <ol class="list-group list-group-flush">
          <li v-if="remotesLoading" class="list-group-item text-muted text-center p-3">
            <i class="fas fa-spinner fa-spin"></i>
          </li>
          <li v-else-if="orgRemotes.length === 0" class="list-group-item text-muted">
            No {{ selectedOrgTab }} remotes.
          </li>
          <li
            v-else
            v-for="remote in orgRemotes"
            :key="remote.id"
            class="list-group-item d-flex align-items-center justify-content-between"
          >
            <GitHubRemoteItem
              :codebase-identifier="codebaseIdentifier"
              :remote="remote"
              @changed="fetchRemotes"
            />
          </li>
        </ol>
      </div>
      <div>
        <button class="btn btn-link ps-0 mb-3" @click="showOrgRemoteForm = !showOrgRemoteForm">
          <i v-if="showOrgRemoteForm" class="fas fa-minus"></i>
          <i v-else class="fas fa-plus"></i>
          Create a new repository
        </button>
        <GitHubRemoteCreateForm
          v-if="showOrgRemoteForm"
          :codebase-identifier="codebaseIdentifier"
          :owner="githubOrgName"
          :default-repo-name="defaultRepoName"
          :is-user-repo="false"
          @success="fetchRemotes"
        />
      </div>
    </div>
    <div class="col">
      <h3><i class="fas fa-user"></i> Repositories on your GitHub account</h3>
      <p>
        Since user-owned repositories give you full control and the ability to make changes, they
        can <b><u>push</u></b> new CML releases to GitHub, and <b><u>archive</u></b> new GitHub
        releases back to the CML. This lets you move your model development to GitHub while still
        keeping it accessible on CoMSES.
      </p>
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
            No {{ selectedUserTab }} remotes.
          </li>
          <li
            v-else
            v-for="remote in userRemotes"
            :key="remote.id"
            class="list-group-item d-flex align-items-center justify-content-between"
          >
            <GitHubRemoteItem
              :codebase-identifier="codebaseIdentifier"
              :remote="remote"
              @changed="fetchRemotes"
            />
          </li>
        </ol>
      </div>
      <div>
        <!-- TODO: guide through connecting account and installing app -->
        <button
          class="btn btn-link ps-0 mb-3"
          @click="showUserRemoteForm = !showUserRemoteForm"
          :disabled="!installationStatus?.githubAccount"
        >
          <i v-if="showUserRemoteForm" class="fas fa-minus"></i>
          <i v-else class="fas fa-plus"></i>
          Create a new repository
        </button>
        <GitHubRemoteCreateForm
          v-if="showUserRemoteForm && githubUsername"
          :codebase-identifier="codebaseIdentifier"
          :owner="githubUsername"
          :default-repo-name="defaultRepoName"
          :is-user-repo="true"
          @success="fetchRemotes"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import type { GitHubAppInstallationStatus, CodebaseGitRemote } from "@/types";
import GitHubRemoteItem from "@/components/GitHubRemoteItem.vue";
import GitHubRemoteCreateForm from "./GitHubRemoteCreateForm.vue";

const props = defineProps<{
  codebaseIdentifier: string;
  githubOrgName: string;
  defaultRepoName: string;
}>();

const { list, getSubmitterInstallationStatus } = useGitRemotesAPI(props.codebaseIdentifier);

const installationStatus = ref<GitHubAppInstallationStatus | null>(null);
const githubUsername = computed(() => installationStatus.value?.githubAccount?.username);

const showOrgRemoteForm = ref(false);
const showUserRemoteForm = ref(false);

const remotesLoading = ref(true);
const remotes = ref<CodebaseGitRemote[]>([]);
const activeOrgRemotes = computed(() => remotes.value.filter(r => !r.isUserRepo && r.isActive));
const inactiveOrgRemotes = computed(() => remotes.value.filter(r => !r.isUserRepo && !r.isActive));
const activeUserRemotes = computed(() => remotes.value.filter(r => r.isUserRepo && r.isActive));
const inactiveUserRemotes = computed(() => remotes.value.filter(r => r.isUserRepo && !r.isActive));

const selectedOrgTab = ref<"active" | "inactive">("active");
const selectedUserTab = ref<"active" | "inactive">("active");
const orgRemotes = computed(() => {
  if (selectedOrgTab.value === "inactive") {
    return inactiveOrgRemotes.value;
  } else {
    return activeOrgRemotes.value;
  }
});
const userRemotes = computed(() => {
  if (selectedUserTab.value === "inactive") {
    return inactiveUserRemotes.value;
  } else {
    return activeUserRemotes.value;
  }
});

const fetchRemotes = async () => {
  remotesLoading.value = true;
  remotes.value = (await list()).data;
  remotesLoading.value = false;
};

onMounted(async () => {
  installationStatus.value = (await getSubmitterInstallationStatus()).data;
  await fetchRemotes();
});
</script>
