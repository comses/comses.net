<template>
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
            No {{ selectedOrgTab }} repos.
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
      <GitHubSetupOrgRemoteWizard
        :codebase-identifier="codebaseIdentifier"
        :owner="githubOrgName"
        :default-repo-name="defaultRepoName"
        @success="fetchRemotes"
      />
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
            No {{ selectedUserTab }} repos.
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
      <GitHubSetupUserRemoteWizard
        class="mb-3"
        :codebase-identifier="codebaseIdentifier"
        :default-repo-name="defaultRepoName"
        :installation-status="installationStatus"
        :from-existing="false"
        @success="fetchRemotes"
      />
      <GitHubSetupUserRemoteWizard
        :codebase-identifier="codebaseIdentifier"
        :default-repo-name="defaultRepoName"
        :installation-status="installationStatus"
        :from-existing="true"
        @success="fetchRemotes"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import type { GitHubAppInstallationStatus, CodebaseGitRemote } from "@/types";
import GitHubRemoteItem from "@/components/GitHubRemoteItem.vue";
import GitHubSetupOrgRemoteWizard from "@/components/GitHubSetupOrgRemoteWizard.vue";
import GitHubSetupUserRemoteWizard from "@/components/GitHubSetupUserRemoteWizard.vue";

const props = defineProps<{
  codebaseIdentifier: string;
  githubOrgName: string;
  defaultRepoName: string;
}>();

const { list, getSubmitterInstallationStatus } = useGitRemotesAPI(props.codebaseIdentifier);

const installationStatus = ref<GitHubAppInstallationStatus>({
  githubAccount: null,
  installationUrl: null,
  connectUrl: "",
});

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
