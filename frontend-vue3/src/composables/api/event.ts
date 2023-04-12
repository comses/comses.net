import { toRefs } from "vue";
import { useAxios } from "@/composables/api/axios";

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
    return get(detailUrl(id));
  }

  async function update(id: string | number, data: any) {
    return put(detailUrl(id), data);
  }

  async function create(data: any) {
    return post(baseUrl, data);
  }

  async function _delete(id: string | number) {
    return del(detailUrl(id));
  }

  return {
    ...toRefs(state),
    retrieve,
    update,
    create,
    delete: _delete,
    searchUrl: searchUrl<EventQueryParams>,
  };
}
