import { toRefs } from "vue";
import { useAxios } from "@/composables/api";
import type { RequestOptions } from "@/composables/api";

export function useProgrammingLanguageAPI() {
  /**
   * Composable function for making requests to the programming languages API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/programming-languages/";
  const { state, get, post, put, detailUrl, searchUrl } = useAxios(baseUrl);

  async function list() {
    return get(baseUrl);
  }

  async function retrieve(id: string | number) {
    return get(detailUrl(id));
  }

  async function create(data: any, options?: RequestOptions) {
    return post(baseUrl, data, options);
  }

  async function update(id: string | number, data: any, options?: RequestOptions) {
    return put(detailUrl(id), data, options);
  }

  return {
    ...toRefs(state),
    list,
    retrieve,
    create,
    update,
    detailUrl,
    searchUrl,
  };
}
