import { useAxios, type RequestOptions } from "@/composables/api";
import { toRefs } from "vue";
import type { UserSearchQueryParams } from "@/types";

export function useProfileAPI() {
  /**
   * Composable function for making requests to the profile API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/users/";
  const { state, get, postForm, put, detailUrl, searchUrl } = useAxios(baseUrl);

  async function search(params: UserSearchQueryParams) {
    return get(searchUrl(params));
  }

  async function retrieve(id: string | number) {
    return get(detailUrl(id));
  }

  async function update(id: string | number, data: any, options?: RequestOptions) {
    return put(detailUrl(id), data, options);
  }

  async function uploadProfilePicture(id: string | number, file: any) {
    const formData = new FormData();
    formData.append("file", file);
    return postForm(detailUrl(id, ["upload_picture"]), formData, {
      config: {
        headers: { "Content-Type": "multipart/form-data" },
      },
    });
  }

  return {
    ...toRefs(state),
    search,
    retrieve,
    update,
    uploadProfilePicture,
    detailUrl,
    searchUrl: searchUrl<UserSearchQueryParams>,
  };
}
