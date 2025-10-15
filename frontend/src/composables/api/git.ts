import { toRefs } from "vue";
import { useAxios, joinPaths, type RequestOptions } from "@/composables/api";
import type {
  CodebaseGitRemote,
  CodebaseGitRemoteForm,
  GitHubAppInstallationStatus,
} from "@/types";
import type { AxiosResponse } from "axios";

export function useGitRemotesAPI(codebaseIdentifier: string) {
  /**
   * Composable function for making requests to the codebase release API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = `/codebases/${codebaseIdentifier}/git/remotes/`;
  const { state, get, post, put, detailUrl } = useAxios(baseUrl);

  function url(paths: string[] = []) {
    return joinPaths([baseUrl, ...paths]);
  }

  async function getSubmitterInstallationStatus(
    options?: RequestOptions
  ): Promise<AxiosResponse<GitHubAppInstallationStatus>> {
    return get(url(["submitter_installation_status"]), options);
  }

  async function list(options?: RequestOptions): Promise<AxiosResponse<CodebaseGitRemote[]>> {
    return get(baseUrl, options);
  }

  async function update(id: number, data: CodebaseGitRemoteForm, options?: RequestOptions) {
    return put(detailUrl(id), data, options);
  }

  async function setupUserGithubRemote(repoName: string, options?: RequestOptions) {
    return post(url(["setup_user_github_remote"]), { repoName }, options);
  }

  async function setupUserExistingGithubRemote(repoName: string, options?: RequestOptions) {
    return post(url(["setup_user_existing_github_remote"]), { repoName }, options);
  }

  return {
    ...toRefs(state),
    detailUrl,
    list,
    update,
    getSubmitterInstallationStatus,
    setupUserGithubRemote,
    setupUserExistingGithubRemote,
  };
}
