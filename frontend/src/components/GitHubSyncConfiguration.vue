<template>
  <hr />
  <div class="row">
    <div class="col border-end">
      <h3><i class="fas fa-university"></i> Repositories in the CoMSES organization</h3>
      <p>
        {{ githubOrgName }}
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut
        labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco
        laboris nisi ut aliquip ex ea commodo consequat.
      </p>
      <div class="card">
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
          <li v-if="orgRemotes.length === 0" class="list-group-item text-muted">
            No {{ selectedOrgTab }} remotes.
          </li>
          <li
            v-else
            v-for="remote in orgRemotes"
            :key="remote.id"
            class="list-group-item d-flex align-items-center justify-content-between"
          >
            <GitHubRemoteItem :remote="remote" />
          </li>
        </ol>
      </div>
    </div>
    <div class="col">
      <h3><i class="fas fa-user"></i> Repositories on your GitHub account</h3>
      <p>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut
        labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco
        laboris nisi ut aliquip ex ea commodo consequat.
      </p>
      <div class="card">
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
          <li v-if="userRemotes.length === 0" class="list-group-item text-muted">
            No {{ selectedUserTab }} remotes.
          </li>
          <li
            v-else
            v-for="remote in userRemotes"
            :key="remote.id"
            class="list-group-item d-flex align-items-center justify-content-between"
          >
            <GitHubRemoteItem :remote="remote" />
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import type {
  GitHubAppInstallationStatus,
  CodebaseGitRemote,
  CodebaseGitRemoteForm,
} from "@/types";
import GitHubRemoteItem from "@/components/GitHubRemoteItem.vue";

const props = defineProps<{
  codebaseIdentifier: string;
  githubOrgName: string;
}>();

const {
  isLoading,
  serverErrors,
  list,
  update,
  getSubmitterInstallationStatus,
  setupOrgGithubRemote,
  setupUserGithubRemote,
} = useGitRemotesAPI(props.codebaseIdentifier);

const installationStatus = ref<GitHubAppInstallationStatus | null>(null);
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
  remotes.value = (await list()).data;
};

onMounted(async () => {
  installationStatus.value = (await getSubmitterInstallationStatus()).data;
  await fetchRemotes();
});
</script>
