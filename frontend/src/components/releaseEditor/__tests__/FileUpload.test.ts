import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import FileUpload from "../FileUpload.vue";

const api = vi.hoisted(() => ({
  uploadFile: vi.fn(),
  serverErrors: { value: [] as string[] },
}));

vi.mock("@/composables/api", () => ({ useReleaseEditorAPI: () => api }));

function mountUpload() {
  return mount(FileUpload, {
    props: {
      title: "Upload model files",
      instructions: "",
      uploadUrl: "/files/package/",
      acceptedFileTypes: "*/*",
      category: "package",
      originals: [],
      hideFileList: true,
    },
  });
}

describe("FileUpload", () => {
  beforeEach(() => {
    api.uploadFile.mockReset();
    api.serverErrors.value = [];
  });

  it("reports partial success and keeps the failed filename with its error", async () => {
    api.uploadFile.mockImplementation(async (_url, file: File) => {
      api.serverErrors.value = file.name === "bad.zip" ? ["Cannot unpack this archive."] : [];
    });
    const wrapper = mountUpload();
    const input = wrapper.get("input");
    const files = [new File(["code"], "model.py"), new File(["broken"], "bad.zip")];
    Object.defineProperty(input.element, "files", { value: files });
    await input.trigger("change");
    await flushPromises();

    expect(api.uploadFile.mock.calls.map(call => call.slice(0, 2))).toEqual(
      files.map(file => ["/files/package/", file])
    );
    expect(wrapper.emitted("uploadDone")).toHaveLength(1);
    expect(wrapper.get('[role="status"]').text()).toContain("1 of 2 files uploaded");
    expect(wrapper.get('[role="alert"]').text()).toContain("bad.zip: Cannot unpack this archive.");
    expect((input.element as HTMLInputElement).disabled).toBe(false);
  });

  it("rejects dropped folders without starting an upload", async () => {
    const wrapper = mountUpload();
    await wrapper.get(".upload-dropzone").trigger("drop", {
      dataTransfer: {
        items: [{ webkitGetAsEntry: () => ({ isDirectory: true }) }],
        files: [],
      },
    });

    expect(api.uploadFile).not.toHaveBeenCalled();
    expect(wrapper.get('[role="alert"]').text()).toContain("ZIP or tar archive");
  });

  it("ignores additional drops while a batch is uploading", async () => {
    let finishUpload!: () => void;
    api.uploadFile.mockReturnValue(new Promise<void>(resolve => (finishUpload = resolve)));
    const wrapper = mountUpload();
    const dropzone = wrapper.get(".upload-dropzone");
    const drop = { dataTransfer: { items: [], files: [new File(["code"], "model.py")] } };
    await dropzone.trigger("drop", drop);
    expect(wrapper.get("input").attributes("disabled")).toBeDefined();
    await dropzone.trigger("drop", drop);
    expect(api.uploadFile).toHaveBeenCalledTimes(1);
    finishUpload();
    await flushPromises();
    expect(wrapper.emitted("uploadDone")).toHaveLength(1);
  });
});
