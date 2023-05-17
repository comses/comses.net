import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type { CodebaseReleaseEditorState, CodebaseRelease, CodebaseReleaseFiles } from "@/types";
import { useCodebaseAPI, useReleaseEditorAPI } from "@/composables/api";

export const useReleaseEditorStore = defineStore("releaseEditor", () => {
  const initialState = INITIAL_STATE;

  // state properties
  const files = ref(initialState.files);
  const release = ref(initialState.release);

  // getters
  const identifier = computed(() => {
    return release.value.codebase.identifier;
  });

  const versionNumber = computed(() => {
    return release.value.version_number;
  });

  const detail = computed(() => {
    return {
      documentation: release.value.documentation,
      embargo_end_date: release.value.embargo_end_date,
      os: release.value.os,
      license: release.value.license,
      live: release.value.live,
      platforms: release.value.platforms,
      programming_languages: release.value.programming_languages,
      release_notes: release.value.release_notes,
    };
  });

  const releaseContributors = computed(() => {
    return release.value.release_contributors;
  });

  // actions
  async function fetchCodebaseRelease(identifier: string, versionNumber: string) {
    const { data, retrieve } = useReleaseEditorAPI();
    await retrieve(identifier, versionNumber);
    release.value = data.value as CodebaseRelease;
    console.log(release.value.identifier);
    console.log(data.value);
  }

  async function fetchMediaFiles() {
    const { data, mediaList } = useCodebaseAPI();
    await mediaList(identifier.value);
    files.value.media = data.value.results;
  }

  async function fetchOriginalFiles(category: string) {
    const { data, listOriginalFiles } = useReleaseEditorAPI();
    await listOriginalFiles(identifier.value, versionNumber.value, category);
    const key = category as keyof CodebaseReleaseFiles["originals"];
    files.value.originals[key] = data.value;
  }

  async function initialize(identifier: string, versionNumber: string) {
    await fetchCodebaseRelease(identifier, versionNumber);
    await fetchMediaFiles();
    if (!release.value.live) {
      for (const category of ["data", "code", "docs", "results"]) {
        await fetchOriginalFiles(category);
      }
    }
  }

  return {
    // state
    files,
    release,
    // getters
    identifier,
    versionNumber,
    detail,
    // actions
    initialize,
    releaseContributors,
    fetchCodebaseRelease,
  };
});

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
    absolute_url: "",
    citationText: "",
    codebase: {
      absolute_url: "",
      all_contributors: [],
      associated_publication_text: "",
      date_created: new Date("2006-01-01"),
      description: "",
      doi: null,
      download_count: 0,
      featured_image: null,
      first_published_at: null,
      id: 0,
      identifier: "",
      last_published_on: null,
      latest_version_number: "",
      peer_reviewed: false,
      references_text: "",
      releases: [],
      replication_text: "",
      repository_url: "",
      submitter: {
        name: "",
        profile_url: "",
        username: "",
      },
      summarized_description: "",
      tags: [],
      title: "",
    },
    date_created: new Date("2006-01-01"),
    dependencies: null,
    documentation: null,
    doi: null,
    embargo_end_date: null,
    first_published_at: null,
    identifier: "",
    last_modified: null,
    last_published_on: null,
    license: null,
    live: false,
    os: "",
    os_display: "",
    peer_reviewed: false,
    platforms: [],
    possible_licenses: [],
    programming_languages: [],
    release_contributors: [],
    release_notes: "",
    review_status: null,
    share_url: null,
    submitted_package: null,
    submitter: {
      name: "",
      profile_url: "",
      username: "",
    },
    urls: {
      request_peer_review: null,
      review: null,
      notify_reviewers_of_changes: null,
    },
    version_number: "",
  },
};
