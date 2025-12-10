<template>
  <div v-if="persistentErrors.length > 0">
    <FormAlert :validation-errors="[]" :server-errors="persistentErrors" />
  </div>
  <div class="d-flex flex-row justify-content-end mb-2">
    <span class="badge bg-transparent border border-blue-gray text-dark me-2">transferred</span>
    <span class="badge bg-blue-gray text-dark">original</span>
  </div>
  <div>
    <div class="table-responsive">
      <table class="table table-borderless align-middle mb-0 w-100" style="table-layout: fixed">
        <colgroup>
          <col style="width: 40%" />
          <col style="width: 20%" />
          <col style="width: 40%" />
        </colgroup>
        <thead>
          <tr>
            <th class="w-40 align-middle text-center">
              <div class="d-inline-flex align-items-center gap-2 justify-content-center">
                <img
                  src="@/assets/images/comses-logo-small.png"
                  alt="CoMSES"
                  style="height: 1.25rem; width: auto"
                />
                <span>Model Library releases</span>
              </div>
            </th>
            <th class="text-center align-middle">
              <div class="d-inline-flex justify-content-center w-100">
                <button
                  v-if="canPush"
                  class="btn btn-primary btn-sm"
                  :disabled="isPushButtonDisabled"
                  @click="handlePushAll"
                >
                  <span v-if="showPushPendingSpinner" class="d-inline-flex align-items-center">
                    <i class="fas fa-spinner fa-spin me-2"></i>
                    Pushing...
                  </span>
                  <span v-else class="d-inline-flex align-items-center">
                    Push pending <i class="fas fa-arrow-right ms-2"></i>
                  </span>
                </button>
              </div>
            </th>
            <th class="w-40 align-middle text-center">
              <div class="d-inline-flex align-items-center gap-2 justify-content-center">
                <i class="fab fa-github"></i>
                <span>GitHub releases</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="localLoading && githubLoading && alignmentRows.length === 0">
            <td colspan="3" class="text-center py-4 text-muted">
              <i class="fas fa-spinner fa-spin me-2"></i>
              Fetching releases...
            </td>
          </tr>
          <tr v-else-if="alignmentRows.length === 0">
            <td colspan="3" class="text-center py-4 text-muted">No releases available</td>
          </tr>
          <tr v-for="[tag, entry] in alignmentRows" :key="tag">
            <td class="align-top">
              <div class="d-flex justify-content-center">
                <LocalReleaseItem
                  v-if="entry.localRelease"
                  :release="entry.localRelease"
                  :is-in-progress="false"
                  :progress="0"
                  @push-started="pollForPushJobs"
                  class="w-100"
                />
                <div v-else style="min-height: 1rem"></div>
              </div>
            </td>
            <td class="text-center align-middle" style="width: 1%; white-space: nowrap">
              <ReleaseSyncStatusCell :entry="entry" @run-import="handleRunImport" />
            </td>
            <td class="align-top">
              <div class="d-flex justify-content-center">
                <GitHubReleaseItem
                  v-if="entry.githubRelease"
                  :release="entry.githubRelease"
                  :codebase-identifier="props.codebaseIdentifier"
                  @import-started="pollForImportJobs"
                  class="w-100"
                />
                <div v-else style="min-height: 1rem"></div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import LocalReleaseItem from "@/components/githubIntegration/LocalReleaseItem.vue";
import GitHubReleaseItem from "@/components/githubIntegration/GitHubReleaseItem.vue";
import ReleaseSyncStatusCell from "@/components/githubIntegration/ReleaseSyncStatusCell.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useGitRemotesAPI } from "@/composables/api/git";
import type {
  GitHubRelease,
  CodebaseReleaseWithGitRefSyncState,
  CodebaseGitRemote,
  ImportedReleaseSyncState,
  ReleaseAlignment,
} from "@/types";

export interface ReleaseManagementSectionProps {
  codebaseIdentifier: string;
  activeRemote: CodebaseGitRemote | null;
  canPush?: boolean;
}

const props = defineProps<ReleaseManagementSectionProps>();

defineEmits<{ "change-remote": [] }>();

const releaseAlignment = ref<ReleaseAlignment>({});
const localLoading = ref(false);
const githubLoading = ref(false);
const pushAllPending = ref(false);

const {
  listLocalReleases,
  listGitHubReleases,
  pushAllReleasesToGitHub,
  importGitHubRelease,
  serverErrors,
} = useGitRemotesAPI(props.codebaseIdentifier);
const persistentErrors = ref<string[]>([]);

const hasActiveRemote = computed(() => !!props.activeRemote);
watch(
  serverErrors,
  newErrors => {
    if (!newErrors?.length) return;
    persistentErrors.value = [...new Set([...persistentErrors.value, ...newErrors])];
  },
  { deep: true }
);

const alignmentRows = computed(() => sortEntries(releaseAlignment.value));

async function handleRunImport(entry: ReleaseAlignment[string], version?: string) {
  if (!entry.githubRelease) return;
  // optimistic client-side status so UI shows running immediately
  const syncState = entry.githubRelease.importedSyncState;
  if (syncState) {
    syncState.status = "RUNNING";
  } else {
    entry.githubRelease.importedSyncState = {
      status: "RUNNING",
      remote: props.activeRemote?.id ?? null,
    } as ImportedReleaseSyncState;
  }
  try {
    await importGitHubRelease(entry.githubRelease.id, version);
    pollForImportJobs();
  } finally {
    // final state will refresh from pollForImportJobs
  }
}

function buildReleaseAlignment(
  localList: CodebaseReleaseWithGitRefSyncState[],
  githubList: GitHubRelease[]
) {
  const matrix: ReleaseAlignment = {};

  localList.forEach(release => {
    const version = release.versionNumber;
    if (!version) return;
    matrix[version] = {
      githubRelease: matrix[version]?.githubRelease ?? null,
      localRelease: release,
    };
  });

  githubList.forEach(release => {
    const versionOrTagName = release.version || release.tagName;
    matrix[versionOrTagName] = {
      githubRelease: release,
      localRelease: matrix[versionOrTagName]?.localRelease ?? null,
    };
  });

  // align by imported GitHub release id when tags/versions differ
  const githubById = new Map<string | number, string>(); // id -> matrix key
  Object.entries(matrix).forEach(([key, entry]) => {
    if (entry.githubRelease) githubById.set(entry.githubRelease.id, key);
  });

  Object.entries(matrix).forEach(([key, entry]) => {
    const importedId = entry.localRelease?.importedReleaseSyncState?.githubReleaseId;
    if (!importedId) return;
    const ghKey = githubById.get(importedId);
    if (!ghKey || ghKey === key) return;

    // move local into the github row if empty, otherwise keep existing
    const target = matrix[ghKey];
    if (!target.localRelease) {
      target.localRelease = entry.localRelease;
      entry.localRelease = null;
    }
  });

  // drop rows that ended up empty after re-alignment
  Object.entries(matrix).forEach(([key, entry]) => {
    if (!entry.localRelease && !entry.githubRelease) delete matrix[key];
  });

  releaseAlignment.value = matrix;
}

function parseSemver(version: string | undefined | null) {
  if (!version) return null;
  const match = version.trim().match(/^v?(\d+)\.(\d+)\.(\d+)$/);
  if (!match) return null;
  return match.slice(1).map(n => Number.parseInt(n, 10)) as [number, number, number];
}

function entryDateMs(entry: ReleaseAlignment[string]) {
  const gh = entry.githubRelease;
  const local = entry.localRelease;
  const ghDate = gh?.publishedAt || gh?.createdAt;
  const localDate = (local as any)?.dateCreated;
  const raw = ghDate || localDate;
  if (!raw) return 0;
  const d = raw instanceof Date ? raw : new Date(raw);
  const t = d.getTime();
  return Number.isNaN(t) ? 0 : t;
}

function sortEntries(matrix: ReleaseAlignment) {
  return Object.entries(matrix).sort((a, b) => {
    const [tagA, entryA] = a;
    const [tagB, entryB] = b;

    const semverA = parseSemver(tagA);
    const semverB = parseSemver(tagB);
    const dateA = entryDateMs(entryA);
    const dateB = entryDateMs(entryB);

    if (semverA && semverB) {
      if (semverA[0] !== semverB[0]) return semverB[0] - semverA[0];
      if (semverA[1] !== semverB[1]) return semverB[1] - semverA[1];
      if (semverA[2] !== semverB[2]) return semverB[2] - semverA[2];
      if (dateA !== dateB) return dateB - dateA;
      return tagA.localeCompare(tagB);
    }

    // Mixed semver/non-semver or both non-semver: order by newest first
    if (dateA !== dateB) return dateB - dateA;
    if (semverA && !semverB) return -1;
    if (!semverA && semverB) return 1;
    return tagA.localeCompare(tagB);
  });
}

function extractLocalReleases() {
  return alignmentRows.value
    .map(([, entry]) => entry.localRelease)
    .filter((release): release is CodebaseReleaseWithGitRefSyncState => Boolean(release));
}

function extractGithubReleases() {
  return alignmentRows.value
    .map(([, entry]) => entry.githubRelease)
    .filter((release): release is GitHubRelease => Boolean(release));
}

async function refreshRemotes() {
  if (!hasActiveRemote.value) return;
  localLoading.value = true;
  githubLoading.value = true;
  try {
    const [local, github] = await Promise.all([listLocalReleases(), listGitHubReleases()]);
    buildReleaseAlignment(local.data, github.data);
  } finally {
    localLoading.value = false;
    githubLoading.value = false;
  }
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

const hasUnpushedReleases = computed(() =>
  extractLocalReleases().some(r => Boolean(r.gitRefSyncState?.canPush))
);

const hasRunningPushJobs = computed(() => {
  const activeId = props.activeRemote?.id;
  if (!activeId) return false;
  return extractLocalReleases().some(r => {
    const state = r.gitRefSyncState;
    if (!state) return false;
    if (state.remote !== activeId) return false;
    return state.status === "RUNNING";
  });
});

const showPushPendingSpinner = computed(() => pushAllPending.value && !hasRunningPushJobs.value);
const isPushButtonDisabled = computed(
  () => !hasUnpushedReleases.value || pushAllPending.value || hasRunningPushJobs.value
);

function markLocalPushesRunning() {
  extractLocalReleases().forEach(release => {
    const state = release.gitRefSyncState;
    if (!state) return;
    state.status = "RUNNING";
  });
}

const handlePushAll = async () => {
  if (isPushButtonDisabled.value) return;
  pushAllPending.value = true;
  markLocalPushesRunning();
  try {
    await pushAllReleasesToGitHub();
    pollForPushJobs();
  } catch (error) {
    console.log("Failed to push all releases", error);
  } finally {
    pushAllPending.value = false;
  }
};

function hasNoImportJobs(): boolean {
  const activeId = props.activeRemote?.id;
  if (!activeId) return false;
  // check RUNNING jobs for all releases on active remote
  return extractGithubReleases().every(r => {
    const s = r.importedSyncState;
    if (!s) return true;
    if (s.remote !== activeId) return true;
    return s.status !== "RUNNING";
  });
}

function hasNoPushJobs(): boolean {
  return !hasRunningPushJobs.value;
}

async function pollRemotesUntil(successCondition: () => boolean | Promise<boolean>) {
  const timeoutMs = 5 * 60 * 1000; // for 5 min
  const intervalMs = 10 * 1000; // every 10 sec
  const start = Date.now();

  const tick = async () => {
    await refreshRemotes();
    const ok = await successCondition();
    if (!ok && Date.now() - start < timeoutMs) setTimeout(tick, intervalMs);
  };
  tick();
}

const pollForImportJobs = async () => pollRemotesUntil(() => hasNoImportJobs());
const pollForPushJobs = async () => pollRemotesUntil(() => hasNoPushJobs());
</script>
