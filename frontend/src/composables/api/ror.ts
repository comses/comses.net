import { toRefs } from "vue";
import { useAxios } from "@/composables/api";
import type { Organization, RORItem } from "@/types";

export function useRORAPI() {
  /**
   * Composable function for making requests to the Research Organization Registry REST API
   * https://ror.readme.io/v2/docs/rest-api
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "https://api.ror.org/v2/organizations";
  const { state, get, searchUrl } = useAxios(baseUrl);

  async function search(query: string): Promise<Organization[]> {
    const response = await get(searchUrl({ query }));
    const data = response.data;
    const orgs = data.items.map((item: RORItem) => {
      const org: Organization = {
        name: "",
        rorId: item.id,
        types: item.types,
        aliases: [],
        acronyms: [],
        link: "",
        url: "",
        wikipediaUrl: "",
        wikidata: item.external_ids?.find(id => id.type === "wikidata")?.all || [],
        location: item.locations[0],
      };
      const geonamesDetails = org.location?.geonames_details;
      if (geonamesDetails && geonamesDetails.lat && geonamesDetails.lng) {
        org.coordinates = {
          lat: geonamesDetails.lat,
          lon: geonamesDetails.lng,
        };
      }
      for (const name of item.names) {
        if (name.types.includes("ror_display")) {
          org.name = name.value;
        } else if (name.types.includes("alias")) {
          org.aliases?.push(name.value);
        } else if (name.types.includes("acronym")) {
          org.acronyms?.push(name.value);
        }
      }
      for (const link of item.links ?? []) {
        if (link.type === "website") {
          org.url = org.link = link.value;
        } else if (link.type === "wikipedia") {
          org.wikipediaUrl = link.value;
        }
      }
      return org;
    });
    return orgs;
  }

  return {
    ...toRefs(state),
    search,
  };
}
