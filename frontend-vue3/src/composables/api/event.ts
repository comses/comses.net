import { toRefs } from "vue";
import { useAxios, type RequestOptions } from "@/composables/api/axios";
import { parseDates } from "@/util";

interface EventQueryParams {
  query?: string;
  start_date__gte?: string;
  submission_deadline__gte?: string;
  tags?: string[];
}

export function useEventAPI() {
  /**
   * Composable function for making requests to the events API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/events/";
  const { state, get, post, put, del, detailUrl, searchUrl } = useAxios(baseUrl);

  async function retrieve(id: string | number) {
    return get(detailUrl(id), {
      parser: data => {
        parseDates(data, [
          "early_registration_deadline",
          "registration_deadline",
          "submission_deadline",
          "start_date",
          "end_date",
          "last_modified",
        ]);
      },
    });
  }

  async function update(id: string | number, data: any, options?: RequestOptions) {
    return put(detailUrl(id), data, options);
  }

  async function create(data: any, options?: RequestOptions) {
    return post(baseUrl, data, options);
  }

  async function _delete(id: string | number) {
    return del(detailUrl(id));
  }

  async function listCalendarEvents(start: Date, end: Date) {
    const toDateStr = (d: Date) => d.toISOString().split("T")[0];
    try {
      const response = await get(
        `${baseUrl}calendar/?start=${toDateStr(start)}&end=${toDateStr(end)}`,
        {
          config: {
            headers: { "Content-Type": "application/json" },
          },
        }
      );
      if (response.status === 200 && response.data) {
        return response.data;
      } else {
        throw new Error("Error fetching calendar events");
      }
    } catch (e) {
      throw new Error("Error fetching calendar events");
    }
  }

  return {
    ...toRefs(state),
    retrieve,
    update,
    create,
    delete: _delete,
    listCalendarEvents,
    detailUrl,
    searchUrl: searchUrl<EventQueryParams>,
  };
}
