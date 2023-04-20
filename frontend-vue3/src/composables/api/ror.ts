import { toRefs } from "vue";
import { useAxios } from "@/composables/api/axios";

interface RORItem {
  id: string;
  name: string;
  email_address?: string;
  ip_addresses?: any[];
  established?: number | null;
  types: string[];
  relationships: any[];
  addresses: any[];
  links: string[];
  aliases: string[];
  acronyms: string[];
  status: "Active" | "Inactive" | "Withdrawn";
  wikipedia_url?: string;
  labels: string[];
  country: object;
  external_ids: any;
  [x: string | number | symbol]: unknown;
}

export interface Organization {
  name: string;
  url?: string;
  acronym?: string;
  ror_id?: string;
}

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
        ror_id: item.id,
      };
    });
    return orgs;
  }

  return {
    ...toRefs(state),
    search,
  };
}
