import { toRefs } from "vue";
import { useAxios } from "@/composables/api";
import type { Organization, RORItem } from "@/types";

export function useRORAPI() {
  /**
   * Composable function for making requests to the Research Organization Registry REST API
   * https://ror.readme.io/docs/rest-api
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "https://api.ror.org/organizations";
  const { state, get, searchUrl } = useAxios(baseUrl);

  async function search(query: string): Promise<Organization[]> {
    const response = await get(searchUrl({ query }));
    const data = response.data;
    const orgs = data.items.map((item: RORItem) => {
      return {
        name: item.name,
        url: item.links[0],
        acronym: item.acronyms[0],
        rorId: item.id,
      };
    });
    return orgs;
  }

  return {
    ...toRefs(state),
    search,
  };
}
