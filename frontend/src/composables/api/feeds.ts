import { toRefs } from "vue";
import { useAxios } from "@/composables/api";
import { parseDates } from "@/util";
import type { FeedItem } from "@/types";

export function useFeedAPI() {
  /**
   * Composable function for making requests to the homepage feed API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/api/feeds/";
  const { state, get } = useAxios(baseUrl);

  async function getFeed(url: string, limit?: number): Promise<{ data: { items: FeedItem[] } }> {
    let requestUrl = url;
    if (limit !== undefined && limit > 0) {
      requestUrl = `${url}?limit=${limit}`;
    }
    return get(requestUrl, {
      parser: data => {
        for (const item of data.items) {
          parseDates(item, ["date"]);
        }
      },
    });
  }

  return {
    ...toRefs(state),
    getFeed,
  };
}
