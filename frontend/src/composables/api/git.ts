import { toRefs } from "vue";
import { useAxios, joinPaths, type RequestOptions } from "@/composables/api";
import type {
  CodebaseGitRemote,
  CodebaseReleaseWithGitRefSyncState,
  GitHubAppInstallationStatus,
  GitHubRelease,
} from "@/types";
import type { AxiosResponse } from "axios";

export function useGitRemotesAPI(codebaseIdentifier: string) {
  /**
   * Composable function for making requests to the codebase release API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = `/codebases/${codebaseIdentifier}/git/remotes/`;
  const { state, get, post, detailUrl } = useAxios(baseUrl);

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

  async function setupUserGithubRemote(
    repoName: string,
    isPreexisting: boolean,
    options?: RequestOptions
  ) {
    return post(
      url(["setup_user_github_remote"]),
      { repoName, is_preexisting: isPreexisting },
      options
    );
  }

  async function getActiveRemote(
    options?: RequestOptions
  ): Promise<AxiosResponse<CodebaseGitRemote>> {
    return get(url(["active_remote"]), options);
  }

  async function buildLocalRepo(options?: RequestOptions) {
    return post(url(["build_local_repo"]), {}, options);
  }

  async function listLocalReleases(
    options?: RequestOptions
  ): Promise<AxiosResponse<CodebaseReleaseWithGitRefSyncState[]>> {
    return get(url(["local_releases"]), options);
  }

  async function listGitHubReleases(
    options?: RequestOptions
  ): Promise<AxiosResponse<GitHubRelease[]>> {
    return get(url(["github_releases"]), options);
  }

  async function importGitHubRelease(
    githubReleaseId: string | number,
    customVersion?: string,
    options?: RequestOptions
  ) {
    return post(
      url(["import_github_release"]),
      {
        github_release_id: githubReleaseId,
        custom_version: customVersion,
      },
      options
    );
  }

  async function pushAllReleasesToGitHub(options?: RequestOptions) {
    return post(url(["push_all"]), {}, options);
  }

  return {
    ...toRefs(state),
    detailUrl,
    list,
    getSubmitterInstallationStatus,
    setupUserGithubRemote,
    getActiveRemote,
    buildLocalRepo,
    listLocalReleases,
    listGitHubReleases,
    importGitHubRelease,
    pushAllReleasesToGitHub,
  };
}
