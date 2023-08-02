import { useAxios } from "@/composables/api";
import { toRefs } from "vue";
import type { UserSearchQueryParams } from "@/types";

export function useContributorAPI() {
  /**
   * Composable function for making requests to the contributor API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/contributors/";
  const { state, get, searchUrl } = useAxios(baseUrl);

  async function search(params: UserSearchQueryParams) {
    params.page = params.page || 1;
    return get(searchUrl(params));
  }

  return {
    ...toRefs(state),
    search,
  };
}
