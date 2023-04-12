import { useAxios } from "@/composables/api/axios";
import { toRefs } from "vue";

interface ProfileQueryParams {
  query?: string;
  page: number;
}

export function useProfileAPI() {
  /**
   * Composable function for making requests to the profile API
   *
   * @returns - An object containing reactive state of the request and helper functions for API requests
   */

  const baseUrl = "/users/";
  const { state, get, postForm, put, detailUrl, searchUrl } = useAxios(baseUrl);

  async function search(params: ProfileQueryParams) {
    return get(searchUrl(params));
  }

  async function retrieve(id: string | number) {
    return get(detailUrl(id));
  }

  async function update(id: string | number, data: any) {
    return put(detailUrl(id), data);
  }

  async function uploadProfilePicture(id: string | number, file: any) {
    const formData = new FormData();
    formData.append("file", file);
    return postForm(`${detailUrl(id)}upload_picture/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }

  return {
    ...toRefs(state),
    search,
    retrieve,
    update,
    uploadProfilePicture,
    searchUrl: searchUrl<ProfileQueryParams>,
  };
}
