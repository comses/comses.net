import { useAxios } from "@/composables/api";
import { toRefs } from "vue";

interface ContributorQueryParams {
  query?: string;
  page: number;
}

export function useContributorAPI() {
  /**
   * Composable function for making requests to the contributor API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/contributors/";
  const { state, get, searchUrl } = useAxios(baseUrl);

  async function search(params: ContributorQueryParams) {
    return get(searchUrl(params));
  }

  return {
    ...toRefs(state),
    search,
  };
}
