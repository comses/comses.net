import queryString from "query-string";
import { useAxios } from "@/composables/api/axios";

export type Tags = { name: string }[];

interface TagQueryParams {
  query: string;
  type: string;
  page: number;
}

export function useTagsAPI() {
  /**
   * Tags API retrieves a list of tags for a given query
   * type is one of Event, Job, Codebase, Profile, or empty string for all
   */

  const baseUrl = "/tags/";
  const { api } = useAxios(baseUrl);

  function listUrl(params: TagQueryParams) {
    const qs = queryString.stringify(params);
    return `?${qs}`;
  }

  async function list(query: string, type="", page=1) {
    return api.get(listUrl({ query, type, page }));
  }

  return {
    list,
 }
}
