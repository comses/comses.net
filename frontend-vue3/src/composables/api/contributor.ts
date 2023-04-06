import { useAxios } from "@/composables/api/axios";
import { toRefs } from "vue";

interface ContributorQueryParams {
  query?: string;
  page: number;
}

export function useContributorAPI() {

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
