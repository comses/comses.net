import queryString from "query-string";
import { useAxios } from "@/composables/api/axios";

export type Tags = { name: string }[];
export type TagType = "" | "Event" | "Codebase" | "Job" | "Profile";
interface TagQueryParams {
  query?: string;
  type?: TagType;
  page?: number;
}

export function useTagsAPI() {
  /**
   * Tags API retrieves a list of tags for a given query
   * type is one of Event, Job, Codebase, Profile, or empty string for all
   */

  const baseUrl = "/tags/";
  const { get, searchUrl } = useAxios(baseUrl);

  async function list(params: TagQueryParams) {
    return get(searchUrl({ type: "", ...params, page: 1 }));
  }

  return {
    list,
  };
}
