import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type {
  CodebaseReleaseEditorState,
  CodebaseRelease,
  CodebaseReleaseFiles,
  CodebaseReleaseMetadata,
  FileCategory,
  RelatedUser,
} from "@/types";
import { useCodebaseAPI, useReleaseEditorAPI } from "@/composables/api";

export const useReleaseEditorStore = defineStore("releaseEditor", () => {
  const initialState = INITIAL_STATE;

  // state properties
  const files = ref(initialState.files);
  const release = ref(initialState.release);

  // property to help determine if the store has been initialized with server data
  const isInitialized = ref(false);

  // getters
  const identifier = computed(() => {
    return release.value.codebase.identifier;
  });

  const versionNumber = computed(() => {
    return release.value.versionNumber;
  });

  const metadata = computed(() => {
    return {
      releaseNotes: release.value.releaseNotes,
      embargoEndDate: release.value.embargoEndDate,
      os: release.value.os,
      platforms: release.value.platforms,
      programmingLanguages: release.value.programmingLanguages,
      outputDataUrl: release.value.outputDataUrl,
      live: release.value.live,
      canEditOriginals: release.value.canEditOriginals,
      license: release.value.license || undefined,
    };
  });

  const releaseContributors = computed(() => {
    return release.value.releaseContributors;
  });

  // actions
  async function fetchCodebaseRelease(identifier: string, versionNumber: string) {
    const { data, retrieve } = useReleaseEditorAPI();
    await retrieve(identifier, versionNumber);
    release.value = data.value as CodebaseRelease;
  }

  function setMetadata(metadata: CodebaseReleaseMetadata) {
    Object.assign(release.value, metadata);
  }

  function getFilesInCategory(category: FileCategory) {
    return files.value.originals[category];
  }

  async function fetchMediaFiles() {
    const { data, mediaList } = useCodebaseAPI();
    await mediaList(identifier.value);
    files.value.media = data.value.results;
  }

  async function fetchOriginalFiles(category: FileCategory) {
    const { data, listOriginalFiles } = useReleaseEditorAPI();
    await listOriginalFiles(identifier.value, versionNumber.value, category);
    const key = category as keyof CodebaseReleaseFiles["originals"];
    files.value.originals[key] = data.value;
  }

  async function deleteFile(category: FileCategory, path: string) {
    const { deleteFile } = useReleaseEditorAPI();
    await deleteFile(path);
    return fetchOriginalFiles(category);
  }

  async function clearCategory(category: FileCategory) {
    const { clearCategory } = useReleaseEditorAPI();
    await clearCategory(identifier.value, versionNumber.value, category);
    return fetchOriginalFiles(category);
  }

  async function initialize(identifier: string, versionNumber: string) {
    isInitialized.value = false;
    await fetchCodebaseRelease(identifier, versionNumber);
    await fetchMediaFiles();
    if (release.value.canEditOriginals) {
      for (const category of ["data", "code", "docs", "results"]) {
        await fetchOriginalFiles(category as FileCategory);
      }
    }
    isInitialized.value = true;
  }

  return {
    // state
    files,
    release,
    isInitialized,
    // getters
    identifier,
    versionNumber,
    metadata,
    // actions
    initialize,
    setMetadata,
    releaseContributors,
    fetchCodebaseRelease,
    fetchOriginalFiles,
    fetchMediaFiles,
    deleteFile,
    clearCategory,
    getFilesInCategory,
  };
});

const DEFAULT_USER: RelatedUser = {
  id: 0,
  username: "",
  memberProfile: {
    id: 0,
    degrees: [],
    givenName: "",
    familyName: "",
    name: "",
    email: "",
    profileUrl: "",
    tags: [],
    username: "",
  },
};

const INITIAL_STATE: CodebaseReleaseEditorState = {
  files: {
    originals: {
      code: [],
      data: [],
      docs: [],
      results: [],
    },
    media: [],
  },
  release: {
    absoluteUrl: "",
    citationText: "",
    codebase: {
      absoluteUrl: "",
      allContributors: [],
      associatedPublicationText: "",
      dateCreated: new Date("2006-01-01"),
      description: "",
      doi: null,
      downloadCount: 0,
      featuredImage: null,
      firstPublishedAt: null,
      id: 0,
      identifier: "",
      lastPublishedOn: null,
      latestVersionNumber: "",
      peerReviewed: false,
      referencesText: "",
      releases: [],
      replicationText: "",
      repositoryUrl: "",
      submitter: DEFAULT_USER,
      summarizedDescription: "",
      tags: [],
      title: "",
    },
    canEditOriginals: false,
    dateCreated: new Date("2006-01-01"),
    dependencies: null,
    documentation: null,
    doi: null,
    embargoEndDate: null,
    firstPublishedAt: null,
    identifier: "",
    lastModified: null,
    lastPublishedOn: null,
    license: null,
    live: false,
    os: "",
    osDisplay: "",
    outputDataUrl: "",
    peerReviewed: false,
    platforms: [],
    possibleLicenses: [],
    programmingLanguages: [],
    releaseContributors: [],
    releaseNotes: "",
    reviewStatus: null,
    shareUrl: null,
    submittedPackage: null,
    submitter: DEFAULT_USER,
    urls: {
      requestPeerReview: null,
      review: null,
      notifyReviewersOfChanges: null,
    },
    versionNumber: "",
  },
};
