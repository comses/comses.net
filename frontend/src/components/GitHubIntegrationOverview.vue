<template>
  <div class="row">
    <h4 class="fw-bold">Your submitted models</h4>
    <div class="col-md-8 col-12 order-2 order-md-1">
      <div class="card" style="height: 15rem">
        <div v-if="loadingCodebases" class="card-body text-center">
          <i class="fas fa-spinner fa-spin"></i> Loading...
        </div>
        <div v-else-if="userCodebases.length === 0" class="card-body text-muted">
          You have not submitted any models yet.
        </div>
        <ul v-else class="list-group list-group-flush" style="overflow-y: auto">
          <li
            v-for="codebase in userCodebases"
            :key="codebase.identifier"
            class="list-group-item d-flex justify-content-between align-items-center gap-3"
          >
            <div class="w-100" style="max-width: 60%">
              <h6 class="mb-0 text-truncate">
                <span v-if="!codebase.live" class="me-2 text-muted" title="Unpublished">
                  <i class="fas fa-lock"></i>
                </span>
                <a :href="codebase.absoluteUrl" :title="codebase.title" class="fw-bold">
                  {{ codebase.title }}
                </a>
              </h6>
              <a
                v-if="codebase.activeGitRemote"
                :href="codebase.activeGitRemote.url"
                class="badge bg-dark mt-1"
                target="_blank"
                rel="noopener noreferrer"
              >
                <i class="fab fa-github me-1"></i>
                {{ codebase.activeGitRemote.owner }}/{{ codebase.activeGitRemote.repoName }}
              </a>
            </div>
            <a
              :href="codebase.githubConfigUrl"
              class="small d-inline-flex align-items-center gap-1 text-nowrap flex-shrink-0"
            >
              <i class="fas fa-cog"></i>
              {{ codebase.activeGitRemote ? "Manage" : "Connect a repository" }}
            </a>
          </li>
        </ul>
      </div>
    </div>
    <div class="col-md-4 col-12 order-1 order-md-2">
      <ConnectGitHubStep :installation-status="installationStatus" style="height: 15rem" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useCodebaseAPI } from "@/composables/api/codebase";
import type { RelatedCodebase, GitHubAppInstallationStatus } from "@/types";
import ConnectGitHubStep from "@/components/githubIntegration/ConnectGitHubStep.vue";

const { submittedCodebases, getGitHubInstallationStatus } = useCodebaseAPI();

const loadingCodebases = ref(true);
const userCodebases = ref<RelatedCodebase[]>([]);
const installationStatus = ref<GitHubAppInstallationStatus>({
  githubAccount: null,
  installationUrl: null,
  connectUrl: "",
});

onMounted(async () => {
  loadingCodebases.value = true;
  try {
    const [codebasesResponse, installationStatusResponse] = await Promise.all([
      submittedCodebases(),
      getGitHubInstallationStatus(),
    ]);
    userCodebases.value = codebasesResponse.data;
    installationStatus.value = installationStatusResponse.data;
  } catch (error) {
    console.error("Failed to fetch data:", error);
  } finally {
    loadingCodebases.value = false;
  }
});
</script>
