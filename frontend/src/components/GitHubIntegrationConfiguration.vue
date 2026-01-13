<template>
  <div style="min-height: 60vh">
    <div class="mb-4">
      <div class="accordion" id="githubSyncWizard">
        <ConnectGitHubStep
          :installation-status="installationStatus"
          :collapse="!showConnectStep"
          @redirected="pollForAccount"
        />
        <SelectSyncTypeStep
          :selected-sync-type="selectedSyncType"
          :collapse="!showSelectSyncStep"
          @reset="onRequestChangeSyncType"
          @choice="handleRepoChoice"
          :new-repository-url="newRepositoryUrl"
        />
        <InstallGitHubAppStep
          :has-existing-repo="selectedSyncType === 'existing'"
          :installation-status="installationStatus"
          :collapse="!showAppInstallStep"
          @redirected="pollForInstallation"
        />
        <ConnectRepositoryStep
          :active-remote="activeRemote"
          v-model:repo-name="repoName"
          :is-validating="isValidating"
          :installation-url="installationStatus.installationUrl"
          :collapse="!showRepoConnectStep"
          @connect="handleConnectRepo"
          @disconnect="showDisconnectRemoteModal"
        />
      </div>
      <FormAlert :validation-errors="[]" :server-errors="serverErrors" />
    </div>
    <div v-if="justConnectedRemote && activeRemote" class="alert alert-success" role="alert">
      <i class="fas fa-check-circle me-2"></i>
      <b>Successfully connected to {{ activeRemote.owner }}/{{ activeRemote.repoName }}</b>
      <p class="mb-0 mt-2">
        Manage this connection by importing releases from GitHub or pushing releases to GitHub
        below. Return here in the future by pressing
        <b><i class="fas fa-cog"></i> manage</b> in the GitHub panel on the model page.
      </p>
    </div>
    <div v-if="showReleaseManagement" class="border rounded p-3">
      <ReleaseManagementSection
        :codebase-identifier="codebaseIdentifier"
        :active-remote="activeRemote"
        :can-push="!activeRemote?.isPreexisting"
      />
    </div>
    <BootstrapModal
      id="disconnectRemoteModal"
      ref="disconnectRemoteModal"
      title="Disconnect repository?"
      centered
    >
      <template #body>
        <p>
          This will deactivate the connection to
          <b>{{ activeRemote?.owner }}/{{ activeRemote?.repoName }}</b
          >.
        </p>
        <p>
          If you reconnect to the <b>same</b> repository later, your push history will be preserved.
          However, if you connect to a <b>different</b> repository, push history will be reset.
        </p>
      </template>
      <template #footer>
        <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
        <button
          type="button"
          class="btn btn-danger"
          :disabled="isDisconnecting"
          @click="confirmDisconnectRemote"
        >
          {{ isDisconnecting ? "Disconnecting..." : "Disconnect" }}
        </button>
      </template>
    </BootstrapModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ConnectGitHubStep from "@/components/githubIntegration/ConnectGitHubStep.vue";
import SelectSyncTypeStep from "@/components/githubIntegration/SelectSyncTypeStep.vue";
import InstallGitHubAppStep from "@/components/githubIntegration/InstallGitHubAppStep.vue";
import ConnectRepositoryStep from "@/components/githubIntegration/ConnectRepositoryStep.vue";
import ReleaseManagementSection from "@/components/githubIntegration/ReleaseManagementSection.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import type { GitHubAppInstallationStatus, CodebaseGitRemote } from "@/types";

export interface GitHubSyncConfigurationNewProps {
  codebaseIdentifier: string;
  githubOrgName: string;
  defaultRepoName: string;
  isCodebaseLive: boolean;
}

const props = defineProps<GitHubSyncConfigurationNewProps>();

const {
  getSubmitterInstallationStatus,
  getActiveRemote,
  buildLocalRepo,
  setupUserGithubRemote,
  disconnectRemote,
  serverErrors,
} = useGitRemotesAPI(props.codebaseIdentifier);

const installationStatus = ref<GitHubAppInstallationStatus>({
  githubAccount: null,
  installationUrl: null,
  connectUrl: "",
});
const installationStatusLoading = ref(false);
const selectedSyncType = ref<"existing" | "new" | null>(null);
const activeRemote = ref<CodebaseGitRemote | null>(null);
const activeRemoteLoading = ref(false);
const repoName = ref(""); // input-only repo name
const isValidating = ref(false);
const justConnectedRemote = ref(false);
// releases state is owned by ReleaseManagementSection

const isGitHubConnected = computed(() => !!installationStatus.value.githubAccount);
const appInstalled = computed(() => !!installationStatus.value.githubAccount?.installationId);
const hasActiveRemote = computed(() => !!activeRemote.value);

// step expansion conditions, only the active step should be expanded
const showConnectStep = computed(() => !isGitHubConnected.value);
const showSelectSyncStep = computed(() => isGitHubConnected.value && !selectedSyncType.value);
const showAppInstallStep = computed(
  () => isGitHubConnected.value && selectedSyncType.value && !appInstalled.value
);
const showRepoConnectStep = computed(
  () =>
    isGitHubConnected.value &&
    selectedSyncType.value &&
    appInstalled.value &&
    !hasActiveRemote.value
);
const showReleaseManagement = computed(
  () =>
    isGitHubConnected.value && selectedSyncType.value && appInstalled.value && hasActiveRemote.value
);

const githubUsername = computed(() => installationStatus.value.githubAccount?.username);
const newRepositoryUrl = computed(
  () => `https://github.com/new?owner=${githubUsername.value}&name=${props.defaultRepoName}`
);

const handleRepoChoice = (syncType: "existing" | "new") => {
  if (syncType === "new") {
    buildLocalRepo();
  }
  selectedSyncType.value = syncType;
};

const disconnectRemoteModal = ref();
const pendingAfterDisconnect = ref<null | (() => void)>(null);
const isDisconnecting = ref(false);

function showDisconnectRemoteModal(afterDisconnect?: () => void) {
  pendingAfterDisconnect.value = afterDisconnect || null;
  disconnectRemoteModal.value?.show();
}

async function confirmDisconnectRemote() {
  isDisconnecting.value = true;
  await disconnectRemote({
    onSuccess: () => {
      activeRemote.value = null;
      repoName.value = "";
      justConnectedRemote.value = false;
      if (pendingAfterDisconnect.value) {
        try {
          pendingAfterDisconnect.value();
        } finally {
          pendingAfterDisconnect.value = null;
        }
      }
      disconnectRemoteModal.value?.hide();
    },
  });
  isDisconnecting.value = false;
}

function onRequestChangeSyncType() {
  if (hasActiveRemote.value) {
    // disconnect first, then clear selectedSyncType
    showDisconnectRemoteModal(() => {
      selectedSyncType.value = null;
    });
  } else {
    selectedSyncType.value = null;
  }
}

const pollSubmitterStatusUntil = (
  successCondition: (s: GitHubAppInstallationStatus) => boolean
) => {
  const startTime = Date.now();
  const timeoutMs = 5 * 60 * 1000; // for 5 min
  const intervalMs = 10 * 1000; // every 10 sec

  const poll = async () => {
    try {
      await refreshInstallationStatus();
      if (successCondition(installationStatus.value)) return;
    } catch (_) {
      // ignore
    }
    if (Date.now() - startTime < timeoutMs) setTimeout(poll, intervalMs);
  };
  setTimeout(poll, intervalMs);
};

const pollForInstallation = () => pollSubmitterStatusUntil(s => !!s.githubAccount?.installationId);
const pollForAccount = () => pollSubmitterStatusUntil(s => !!s.githubAccount);

const handleConnectRepo = async () => {
  if (!repoName.value || !selectedSyncType.value) return;
  isValidating.value = true;
  await setupUserGithubRemote(repoName.value.trim(), selectedSyncType.value === "existing", {
    onSuccess: async () => {
      await refreshActiveRemote();
      justConnectedRemote.value = true;
    },
  });
  isValidating.value = false;
};

async function refreshActiveRemote() {
  activeRemoteLoading.value = true;
  try {
    activeRemote.value = (await getActiveRemote()).data;
  } finally {
    activeRemoteLoading.value = false;
  }
}

async function refreshInstallationStatus() {
  installationStatusLoading.value = true;
  try {
    installationStatus.value = (await getSubmitterInstallationStatus()).data;
  } finally {
    installationStatusLoading.value = false;
  }
}

onMounted(async () => {
  await refreshInstallationStatus();
  await refreshActiveRemote();
  if (activeRemote.value) {
    selectedSyncType.value = activeRemote.value.isPreexisting ? "existing" : "new";
  }
});
</script>
