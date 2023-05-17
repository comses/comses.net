import { toRefs } from "vue";
import { useAxios, type RequestOptions } from "@/composables/api";
import { parseDates } from "@/util";

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
    return get(detailUrl(id), {
      parser: data => {
        parseDates(data, ["date_created", "last_modified", "application_deadline"]);
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

  return {
    ...toRefs(state),
    retrieve,
    update,
    create,
    delete: _delete,
    detailUrl,
    searchUrl: searchUrl<JobQueryParams>,
  };
}
