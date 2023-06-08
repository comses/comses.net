import { useAxios } from "@/composables/api";
import type { TagType } from "@/types";

interface TagQueryParams {
  query?: string;
  type?: TagType;
  page?: number;
}

export function useTagsAPI() {
  /**
   * Composable function for making requests to the tags API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/tags/";
  const { get, searchUrl } = useAxios(baseUrl);

  async function search(params: TagQueryParams) {
    return get(searchUrl({ type: "", ...params, page: 1 }));
  }

  return {
    search,
  };
}
