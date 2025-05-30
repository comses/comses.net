import { toRefs } from "vue";
import { useAxios } from "@/composables/api";
import { parseDates } from "@/util";

export function useFeedAPI() {
  /**
   * Composable function for making requests to the homepage feed API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/api/feeds/";
  const { state, get, detailUrl } = useAxios(baseUrl);

  function getCodebases() {
    return get(detailUrl("code"));
  }

  function getEvents() {
    return get(detailUrl("events"), {
      parser: data => {
        for (const item of data.items) {
          parseDates(item, ["date"]);
        }
      },
    });
  }

  function getForumPosts() {
    return get(detailUrl("forum"), {
      parser: data => {
        for (const item of data.items) {
          parseDates(item, ["date"]);
        }
      },
    });
  }

  function getJobs() {
    return get(detailUrl("jobs"), {
      parser: data => {
        for (const item of data.items) {
          parseDates(item, ["date"]);
        }
      },
    });
  }

  function getVideos() {
    return get(detailUrl("yt"));
  }

  return {
    ...toRefs(state),
    getCodebases,
    getEvents,
    getForumPosts,
    getJobs,
    getVideos,
  };
}
