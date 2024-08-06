import { toRefs } from "vue";
import { useAxios, type RequestOptions } from "@/composables/api";

interface CodebaseQueryParams {
  query?: string;
  publishedAfter?: string;
  publishedBefore?: string;
  tags?: string[];
  peerReviewStatus?: string;
  programmingLanguages?: string[];
  ordering?: string;
}

export function useCodebaseAPI() {
  /**
   * Composable function for making requests to the codebase API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/codebases/";
  const { state, get, post, put, del, detailUrl, searchUrl } = useAxios(baseUrl);

  async function create(data: any, options?: RequestOptions) {
    return post(baseUrl, data, options);
  }

  async function retrieve(identifier: string | number) {
    return get(detailUrl(identifier));
  }

  async function update(identifier: string | number, data: any, options?: RequestOptions) {
    return put(detailUrl(identifier), data, options);
  }

  function mediaListUrl(identifier: string) {
    return detailUrl(identifier, ["media"]);
  }

  async function mediaList(identifier: string) {
    return get(mediaListUrl(identifier));
  }

  async function mediaDelete(identifier: string, imageId: string | number) {
    return del(detailUrl(identifier, ["media", imageId]));
  }

  async function mediaClear(identifier: string) {
    return del(detailUrl(identifier, ["media", "clear"]));
  }

  return {
    ...toRefs(state),
    create,
    retrieve,
    update,
    mediaList,
    mediaDelete,
    mediaClear,
    mediaListUrl,
    detailUrl,
    searchUrl: searchUrl<CodebaseQueryParams>,
  };
}
