import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi, beforeEach } from "vitest";

// Mock the codebase API composable so we can capture the sparse payload sent to partialUpdate()
const mockPartialUpdate = vi.fn();
const fullCodebase = {
  id: 42,
  identifier: "abc123",
  title: "My Model",
  description: "A complex model description",
  videoSourceUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  repositoryUrl: "https://github.com/example/repo",
  doi: "10.1234/abc",
  submitter: { id: 1, username: "alice" },
  allContributors: [],
  releases: [],
};

vi.mock("@/composables/api", () => ({
  useCodebaseAPI: () => {
    const dataRef = { value: null as any };
    return {
      data: dataRef,
      mediaListUrl: (identifier: string) => `/codebases/${identifier}/media/`,
      mediaDelete: vi.fn(),
      mediaClear: vi.fn(),
      retrieve: async () => {
        dataRef.value = fullCodebase;
        return { data: fullCodebase };
      },
      partialUpdate: mockPartialUpdate,
    };
  },
  useReleaseEditorAPI: () => ({
    uploadFile: vi.fn(),
    listOriginalFiles: vi.fn(),
    deleteFile: vi.fn(),
    clearCategory: vi.fn(),
  }),
}));

// Mock the release editor store
vi.mock("@/stores/releaseEditor", () => ({
  useReleaseEditorStore: () => ({
    fetchCodebaseRelease: vi.fn(),
    fetchMediaFiles: vi.fn(),
  }),
}));

// Mock Bootstrap Modal (used by BootstrapModal component)
vi.mock("bootstrap/js/dist/modal", () => ({
  default: class {
    show() {}
    hide() {}
  },
}));

import CommonMediaModal from "@/components/releaseEditor/CommonMediaModal.vue";

describe("CommonMediaModal - Save video payload", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("sends only the videoSourceUrl field on save, not the entire codebase object", async () => {
    const wrapper = mount(CommonMediaModal, {
      props: {
        buttonClass: "btn btn-primary",
        identifier: "abc123",
        files: [],
        show: false,
      },
      global: {
        plugins: [createPinia()],
      },
    });

    // Wait for onMounted to complete (retrieve + setValuesWithLoadTime)
    await flushPromises();

    // Find the video URL input and update it
    const input = wrapper.find('input[name="videoSourceUrl"]');
    expect(input.exists()).toBe(true);

    // Change the YouTube URL to a new value
    await input.setValue("https://www.youtube.com/watch?v=abcdefghijk");

    // Submit the form
    const form = wrapper.find("form");
    await form.trigger("submit");
    await flushPromises();

    // Assert that update was called
    expect(mockPartialUpdate).toHaveBeenCalled();

    // The payload sent to partialUpdate() should contain ONLY the videoSourceUrl field,
    // not the entire codebase object with title, description, doi, etc.
    const callArgs = mockPartialUpdate.mock.calls[0];
    const payload = callArgs[1]; // second argument is the data payload

    // This is the regression test: the payload should be a minimal patch
    // containing only { videoSourceUrl: "..." }, not the full codebase object.
    expect(payload).toEqual({
      videoSourceUrl: "https://www.youtube.com/watch?v=abcdefghijk",
    });

    // Explicitly check that unrelated fields are NOT present in the payload
    expect(payload).not.toHaveProperty("title");
    expect(payload).not.toHaveProperty("description");
    expect(payload).not.toHaveProperty("doi");
    expect(payload).not.toHaveProperty("repositoryUrl");
    expect(payload).not.toHaveProperty("submitter");
    expect(payload).not.toHaveProperty("loadedTime");
  });
});
