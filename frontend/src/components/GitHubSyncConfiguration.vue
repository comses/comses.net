<template>
  <div style="min-height: 60vh">
    <div class="row">
      <div class="col-12">
        <h3>Repositories linked with this model</h3>
        <p>
          Only one linked repository can be active at a time. A repository is considered active if
          either pushing or importing is turned on.
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
            <li v-else v-for="remote in userRemotes" :key="remote.id" class="list-group-item">
              <GitHubRemoteItem
                :codebase-identifier="codebaseIdentifier"
                :remote="remote"
                @changed="fetchRemotes"
              />
            </li>
          </ol>
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-12 col-md-6">
        <GitHubSetupUserRemoteWizard
          class="mb-3"
          :codebase-identifier="codebaseIdentifier"
          :default-repo-name="defaultRepoName"
          :installation-status="installationStatus"
          :from-existing="false"
          @success="fetchRemotes"
        />
      </div>
      <div class="col-12 col-md-6">
        <GitHubSetupUserRemoteWizard
          :codebase-identifier="codebaseIdentifier"
          :default-repo-name="defaultRepoName"
          :installation-status="installationStatus"
          :from-existing="true"
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
const activeUserRemotes = computed(() => remotes.value.filter(r => r.isUserRepo && r.isActive));
const inactiveUserRemotes = computed(() => remotes.value.filter(r => r.isUserRepo && !r.isActive));

const selectedUserTab = ref<"active" | "inactive">("active");
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
