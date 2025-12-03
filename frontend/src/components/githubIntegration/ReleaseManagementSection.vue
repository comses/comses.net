<template>
  <div class="space-y-4">
    <div class="row">
      <div class="col-lg-6 mb-4">
        <div class="card h-100">
          <div
            class="card-header d-flex align-items-center justify-content-between"
            style="min-height: 3rem"
          >
            <div>
              <h6 class="card-title d-flex align-items-center gap-2 mb-0">
                <img
                  src="@/assets/images/comses-logo-small.png"
                  alt="CoMSES"
                  style="height: 1.5rem; width: auto"
                />
                Model Library Releases
              </h6>
            </div>
            <button
              v-if="canPush"
              class="btn btn-primary btn-sm"
              :disabled="!hasUnpushedReleases"
              @click="handlePushAll"
            >
              <i class="fas fa-upload me-2"></i>
              Push All
            </button>
          </div>
          <div style="overflow-y: auto">
            <ul class="list-group list-group-flush">
              <template v-if="localLoading && localReleases.length === 0">
                <li class="list-group-item text-center py-4 text-muted">
                  <span>
                    <i class="fas fa-spinner fa-spin me-2"></i>
                    Fetching releases...
                  </span>
                </li>
              </template>
              <template v-else>
                <LocalReleaseItem
                  v-for="release in localReleases"
                  :key="release.identifier"
                  :release="release"
                  :is-in-progress="false"
                  :progress="0"
                  @push-started="pollForPushJobs"
                />
                <li
                  v-if="localReleases.length === 0"
                  class="list-group-item text-center py-4 text-muted"
                >
                  No releases available
                </li>
              </template>
            </ul>
          </div>
        </div>
      </div>

      <div class="col-lg-6 mb-4">
        <div class="card h-100">
          <div
            class="card-header d-flex align-items-center justify-content-between"
            style="min-height: 3rem"
          >
            <h6 class="card-title d-flex align-items-center gap-2 mb-0">
              <i class="fab fa-github"></i>
              GitHub Releases
            </h6>
          </div>
          <div style="overflow-y: auto">
            <ul class="list-group list-group-flush">
              <template v-if="githubLoading && githubReleases.length === 0">
                <li class="list-group-item text-center py-4 text-muted">
                  <span>
                    <i class="fas fa-spinner fa-spin me-2"></i>
                    Fetching releases from GitHub...
                  </span>
                </li>
              </template>
              <template v-else>
                <GitHubReleaseItem
                  v-for="release in githubReleases || []"
                  :key="release.id"
                  :release="release"
                  :codebase-identifier="props.codebaseIdentifier"
                  @import-started="pollForImportJobs"
                />
                <li
                  v-if="!githubReleases || githubReleases.length === 0"
                  class="list-group-item text-center py-4 text-muted"
                >
                  No GitHub releases available
                </li>
              </template>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import LocalReleaseItem from "@/components/githubIntegration/LocalReleaseItem.vue";
import GitHubReleaseItem from "@/components/githubIntegration/GitHubReleaseItem.vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import type { GitHubRelease, CodebaseReleaseWithGitRefSyncState, CodebaseGitRemote } from "@/types";

export interface ReleaseManagementSectionProps {
  codebaseIdentifier: string;
  activeRemote: CodebaseGitRemote | null;
  canPush?: boolean;
}

const props = defineProps<ReleaseManagementSectionProps>();

defineEmits<{ "change-remote": [] }>();

const localReleases = ref<CodebaseReleaseWithGitRefSyncState[]>([]);
const githubReleases = ref<GitHubRelease[]>([]);
const localLoading = ref(false);
const githubLoading = ref(false);

const { listLocalReleases, listGitHubReleases, pushAllReleasesToGitHub } = useGitRemotesAPI(
  props.codebaseIdentifier
);

const hasActiveRemote = computed(() => !!props.activeRemote);

async function refreshLocalReleases() {
  if (!hasActiveRemote.value) return;
  localLoading.value = true;
  try {
    localReleases.value = (await listLocalReleases()).data;
  } finally {
    localLoading.value = false;
  }
}

async function refreshGitHubReleases() {
  if (!hasActiveRemote.value) return;
  githubLoading.value = true;
  try {
    githubReleases.value = (await listGitHubReleases()).data;
  } finally {
    githubLoading.value = false;
  }
}

async function refreshRemotes() {
  await Promise.all([refreshLocalReleases(), refreshGitHubReleases()]);
}

onMounted(() => {
  refreshRemotes();
});

watch(
  () => props.activeRemote?.id,
  () => {
    refreshRemotes();
  }
);

const hasUnpushedReleases = computed(() => localReleases.value.some(r => !!r.gitRefSyncState));

const handlePushAll = async () => {
  await pushAllReleasesToGitHub();
  pollForPushJobs();
};

function hasNoImportJobs(): boolean {
  const activeId = props.activeRemote?.id;
  if (!activeId) return false;
  // check RUNNING jobs for all releases on active remote
  return (githubReleases.value || []).every(r => {
    const s = r.importedSyncState;
    if (!s) return true;
    if (s.remote !== activeId) return true;
    return s.status !== "RUNNING";
  });
}

function hasNoPushJobs(): boolean {
  const activeId = props.activeRemote?.id;
  if (!activeId) return false;
  return localReleases.value.every(r => {
    const state = r.gitRefSyncState;
    if (!state) return true;
    if (state.remote !== activeId) return true;
    return state.status !== "RUNNING";
  });
}

async function pollRemotesUntil(successCondition: () => boolean | Promise<boolean>) {
  const timeoutMs = 5 * 60 * 1000; // for 5 min
  // FIXME: if this times out, something probably went wrong
  const intervalMs = 10 * 1000; // every 10 sec
  const start = Date.now();

  const tick = async () => {
    await refreshRemotes();
    const ok = await successCondition();
    if (!ok && Date.now() - start < timeoutMs) setTimeout(tick, intervalMs);
  };
  tick();
}

const pollForImportJobs = () => pollRemotesUntil(() => hasNoImportJobs());
const pollForPushJobs = () => pollRemotesUntil(() => hasNoPushJobs());
</script>
