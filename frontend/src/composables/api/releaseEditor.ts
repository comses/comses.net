import { toRefs } from "vue";
import { useAxios, type RequestOptions } from "@/composables/api";
import { parseDates } from "@/util";
import type { CodebaseRelease } from "@/types";
import type { AxiosProgressEvent, AxiosError } from "axios";

export function useReleaseEditorAPI() {
  /**
   * Composable function for making requests to the codebase release API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/codebases/";
  const { state, get, post, postForm, put, del, detailUrl } = useAxios(baseUrl);

  function releaseDetailUrl(identifier: string, versionNumber: string, paths: string[] = []) {
    return detailUrl(identifier, ["releases", versionNumber, ...paths]);
  }

  // urls
  function editUrl(identifier: string, versionNumber: string) {
    return releaseDetailUrl(identifier, versionNumber, ["edit"]);
  }
  function detailEditUrl(identifier: string, versionNumber: string) {
    return `${releaseDetailUrl(identifier, versionNumber)}?edit`;
  }
  function listOriginalsFileUrl(identifier: string, versionNumber: string, category: string) {
    return releaseDetailUrl(identifier, versionNumber, ["files", "originals", category]);
  }
  function clearCategoryUrl(identifier: string, versionNumber: string, category: string) {
    return releaseDetailUrl(identifier, versionNumber, [
      "files",
      "originals",
      category,
      "clear_category",
    ]);
  }
  function downloadPreviewUrl(identifier: string, versionNumber: string) {
    return releaseDetailUrl(identifier, versionNumber, ["download_preview"]);
  }
  function downloadUrl(identifier: string, versionNumber: string) {
    return releaseDetailUrl(identifier, versionNumber, ["download"]);
  }
  function downloadRequestUrl(identifier: string, versionNumber: string) {
    return releaseDetailUrl(identifier, versionNumber, ["request_download"]);
  }
  function updateContributorUrl(identifier: string, versionNumber: string) {
    return releaseDetailUrl(identifier, versionNumber, ["contributors"]);
  }

  // requests - CRUD
  async function retrieve(identifier: string, versionNumber: string) {
    return get(detailEditUrl(identifier, versionNumber), {
      parser: (data: CodebaseRelease) => {
        parseDates(data, [
          "dateCreated",
          "firstPublishedAt",
          "embargoEndDate",
          "lastModified",
          "lastPublishedOn",
        ]);
      },
    });
  }

  async function publish(identifier: string, versionNumber: string, data: any) {
    return post(releaseDetailUrl(identifier, versionNumber, ["publish"]), data);
  }

  async function update(identifier: string, versionNumber: string, data: any) {
    return put(detailEditUrl(identifier, versionNumber), data);
  }

  async function clearCategory(identifier: string, versionNumber: string, category: string) {
    return del(clearCategoryUrl(identifier, versionNumber, category));
  }

  async function regenerateShareUUID(identifier: string, versionNumber: string) {
    return post(releaseDetailUrl(identifier, versionNumber, ["regenerate_share_uuid"]));
  }

  async function updateContributors(identifier: string, versionNumber: string, data: any) {
    return put(updateContributorUrl(identifier, versionNumber), data);
  }

  // requests - files
  async function listOriginalFiles(identifier: string, versionNumber: string, category: string) {
    return get(listOriginalsFileUrl(identifier, versionNumber, category));
  }

  async function uploadFile(
    uploadUrl: string,
    file: any,
    onUploadProgress: (progressEvent: AxiosProgressEvent) => void,
    onError: (error: AxiosError) => void
  ) {
    const formData = new FormData();
    formData.append("file", file);
    return postForm(uploadUrl, formData, {
      config: {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress,
      },
      onError,
    });
  }

  async function deleteFile(path: string) {
    return del(path);
  }

  // requests - download
  async function downloadPreview(identifier: string, versionNumber: string) {
    return get(downloadPreviewUrl(identifier, versionNumber));
  }

  async function download(identifier: string, versionNumber: string) {
    return get(downloadUrl(identifier, versionNumber));
  }

  async function requestDownload(
    identifier: string,
    versionNumber: string,
    data: any,
    options?: RequestOptions
  ) {
    return post(downloadRequestUrl(identifier, versionNumber), data, options);
  }

  return {
    ...toRefs(state),
    detailUrl: releaseDetailUrl,
    editUrl,
    detailEditUrl,
    listOriginalsFileUrl,
    clearCategoryUrl,
    downloadPreviewUrl,
    downloadUrl,
    downloadRequestUrl,
    updateContributorUrl,
    retrieve,
    publish,
    update,
    clearCategory,
    regenerateShareUUID,
    updateContributors,
    listOriginalFiles,
    uploadFile,
    deleteFile,
    downloadPreview,
    download,
    requestDownload,
  };
}
