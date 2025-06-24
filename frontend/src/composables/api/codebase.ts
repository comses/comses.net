import { toRefs } from "vue";
import { joinPaths, useAxios, type RequestOptions } from "@/composables/api";
import type { AxiosResponse } from "axios";
import type { GitHubAppInstallationStatus, RelatedCodebase } from "@/types";

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

  function url(paths: string[] = []) {
    return joinPaths([baseUrl, ...paths]);
  }

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

  async function getGitHubInstallationStatus(
    options?: RequestOptions
  ): Promise<AxiosResponse<GitHubAppInstallationStatus>> {
    return get(url(["github_installation_status"]), options);
  }

  async function submittedCodebases(
    options?: RequestOptions
  ): Promise<AxiosResponse<RelatedCodebase[]>> {
    return get(url(["submitted_codebases"]), options);
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
    getGitHubInstallationStatus,
    submittedCodebases,
  };
}
