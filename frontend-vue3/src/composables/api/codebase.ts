import { toRefs } from "vue";
import { useAxios } from "@/composables/api/axios";

interface CodebaseQueryParams {
  query?: string;
  published_after?: string;
  published_before?: string;
  tags?: string[];
  peer_review_status?: string;
}

export function useCodebaseAPI() {
  /**
   * Composable function for making requests to the codebase API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/codebases/";
  const { state, get, post, put, del, detailUrl, searchUrl } = useAxios(baseUrl);

  async function create(data: any) {
    return post(baseUrl, data);
  }

  async function retrieve(identifier: string | number) {
    return get(detailUrl(identifier));
  }

  async function update(identifier: string | number, data: any) {
    return put(detailUrl(identifier), data);
  }

  async function mediaList(identifier: string) {
    return get(`${detailUrl(identifier)}media/`);
  }

  async function mediaDelete(identifier: string, image_id: string | number) {
    return del(`${detailUrl(identifier)}media/${image_id}`);
  }

  async function mediaClear(identifier: string) {
    return del(`${detailUrl(identifier)}media/clear/`);
  }

  return {
    ...toRefs(state),
    create,
    retrieve,
    update,
    mediaList,
    mediaDelete,
    mediaClear,
    searchUrl: searchUrl<CodebaseQueryParams>,
  };
}

export function useReleaseAPI() {
  /**
   * Composable function for making requests to the codebase release API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/codebases/";
  const { state, get, post, postForm, put, del } = useAxios(baseUrl);

  // urls
  // FIXME: this seems overly verbose, we may not even need many of these
  // revisit when implementing components that use this
  function detailUrl(identifier: string, version_number: string) {
    return `${baseUrl}${identifier}/releases/${version_number}/`;
  }
  function editUrl(identifier: string, version_number: string) {
    return `${detailUrl(identifier, version_number)}edit/`;
  }
  function detailEditUrl(identifier: string, version_number: string) {
    return `${detailUrl(identifier, version_number)}?edit/`;
  }
  function listOriginalsFileUrl(identifier: string, version_number: string, category: string) {
    return `${detailUrl(identifier, version_number)}files/originals/${category}/`;
  }
  function clearCategoryUrl(identifier: string, version_number: string, category: string) {
    return `${listOriginalsFileUrl(identifier, version_number, category)}clear_category/`;
  }
  function downloadPreviewUrl(identifier: string, version_number: string) {
    return `${detailUrl(identifier, version_number)}download_preview/`;
  }
  function downloadUrl(identifier: string, version_number: string) {
    return `${detailUrl(identifier, version_number)}download/`;
  }
  function downloadRequestUrl(identifier: string, version_number: string) {
    return `${detailUrl(identifier, version_number)}request_download/`;
  }
  function updateContributorUrl(identifier: string, version_number: string) {
    return `${detailUrl(identifier, version_number)}contributors/`;
  }

  // requests - CRUD
  async function retrieve(identifier: string, version_number: string) {
    return get(detailUrl(identifier, version_number));
  }

  async function publish(identifier: string, version_number: string) {
    return post(`${detailUrl(identifier, version_number)}publish/`);
  }

  async function update(identifier: string, version_number: string, data: any) {
    return put(detailUrl(identifier, version_number), data);
  }

  async function clearCategory(identifier: string, version_number: string, category: string) {
    return del(clearCategoryUrl(identifier, version_number, category));
  }

  async function updateContributors(identifier: string, version_number: string, data: any) {
    return put(updateContributorUrl(identifier, version_number), data);
  }

  // requests - files
  async function listOriginalFiles(identifier: string, version_number: string, category: string) {
    return get(listOriginalsFileUrl(identifier, version_number, category));
  }

  async function uploadFile(
    identifier: string,
    version_number: string,
    category: string,
    file: any,
    onUploadProgress: any
  ) {
    const formData = new FormData();
    formData.append("file", file);
    return postForm(listOriginalsFileUrl(identifier, version_number, category), formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress,
    });
  }

  async function deleteFile(path: string) {
    return del(path);
  }

  // requests - download
  async function downloadPreview(identifier: string, version_number: string) {
    return get(downloadPreviewUrl(identifier, version_number));
  }

  async function download(identifier: string, version_number: string) {
    return get(downloadUrl(identifier, version_number));
  }

  async function requestDownload(identifier: string, version_number: string) {
    return post(downloadRequestUrl(identifier, version_number));
  }

  return {
    ...toRefs(state),
    detailUrl,
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
    updateContributors,
    listOriginalFiles,
    uploadFile,
    deleteFile,
    downloadPreview,
    download,
    requestDownload,
  };
}
