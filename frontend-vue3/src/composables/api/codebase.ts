import { useAxios } from "@/composables/api/axios";

export type Tags = { name: string }[];

interface CodebaseQueryParams {
  query?: string;
  published_after?: string;
  published_before?: string;
  tags?: string[];
  peer_review_status?: string;
}

export function useCodebaseAPI() {
  /**
   * Codebase API
   */

  const baseUrl = "/codebases/";
  const { api, searchUrl } = useAxios(baseUrl);
 
  const _searchUrl = (params: CodebaseQueryParams) => searchUrl(params);

  return {
    searchUrl: _searchUrl,
  }
}

