import { toRefs } from "vue";
import { useAxios } from "@/composables/api/axios";

interface JobQueryParams {
  query?: string;
  date_created__gte?: string;
  application_deadline__gte?: string;
  tags?: string[];
}

export function useJobAPI() {
  /**
   * Composable function for making requests to the jobs API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/jobs/";
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
    searchUrl: searchUrl<JobQueryParams>,
  };
}
