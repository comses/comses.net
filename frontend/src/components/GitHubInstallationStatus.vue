<template>
  <div class="card mb-3">
    <div class="card-header p-3 bg-dark text-white">
      <h5 class="mb-0">Sync requirements</h5>
    </div>
    <div class="d-flex flex-column h-100">
      <div class="list-group list-group-flush">
        <div class="list-group-item p-3">
          <i v-if="!githubAccount" class="fas fa-times-circle text-danger me-2"></i>
          <i v-else class="fas fa-check-circle text-success me-2"></i>
          <span v-if="!githubAccount">GitHub account <u>not connected</u></span>
          <span v-else>
            Connected as
            <a :href="githubAccount.profileUrl" target="_blank" class="badge bg-dark">
              <i class="fab fa-github me-1"></i>
              {{ githubAccount.username }}
            </a>
          </span>
        </div>
        <div class="list-group-item p-3 border-bottom">
          <i v-if="!githubAppInstalled" class="fas fa-times-circle text-danger me-2"></i>
          <i v-else class="fas fa-check-circle text-success me-2"></i>
          CoMSES Sync App
          <u v-if="!githubAppInstalled">not installed</u>
          <u v-else>installed</u>
          <p v-if="!githubAppInstalled && githubAccount" class="small text-muted mb-0 mt-1">
            <small
              >Installed but not recognized? Try refreshing the page or
              <a :href="installationStatus.installationUrl || ''" target="_blank"
                >uninstalling and reinstalling the app</a
              >.
            </small>
          </p>
        </div>
      </div>
      <div
        v-if="showAction"
        class="flex-grow-1 d-flex justify-content-center align-items-center p-3"
      >
        <a v-if="!githubAccount" :href="installationStatus.connectUrl" class="btn btn-secondary">
          <i class="fab fa-github me-2"></i>
          Connect GitHub
        </a>
        <a
          v-else-if="!githubAppInstalled"
          :href="installationStatus.installationUrl || ''"
          target="_blank"
          class="btn btn-primary"
        >
          <i class="fas fa-download me-2"></i>
          Install App
        </a>
        <a
          v-else
          :href="installationStatus.installationUrl || ''"
          target="_blank"
          class="btn btn-outline-secondary"
        >
          <i class="fas fa-cog me-2"></i>
          Manage Installation
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { GitHubAppInstallationStatus } from "@/types";

export interface GitHubInstallationStatusProps {
  installationStatus: GitHubAppInstallationStatus;
  showAction: boolean;
}

const props = withDefaults(defineProps<GitHubInstallationStatusProps>(), {
  showAction: true,
});

const githubAccount = computed(() => props.installationStatus.githubAccount);
const githubAppInstalled = computed(() => !!githubAccount.value?.installationId);
</script>
