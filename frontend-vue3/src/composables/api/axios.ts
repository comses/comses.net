import queryString from "query-string";
import axios, { type AxiosInstance } from "axios";

export function useAxios(baseURL: string) {
  const api = axios.create({ baseURL });

  function detailUrl(id: string | number) {
    return `${baseURL}${id}/`;
  }

  function createUrl() {
    return baseURL;
  }

  function _delete(id: string | number) {
    return api.delete(detailUrl(id));
  }
  
  function retrieve(id: string | number) {
    return api.get(detailUrl(id));
  }
  
  function update(id: string | number) {
    return api.put(detailUrl(id));
  }

  function create() {
    return api.post(createUrl());
  }

  function searchUrl<QueryParams extends Record<string, any>>(params: QueryParams) {
    // filter out falsy values (empty strings, etc)
    const filteredParams: Partial<QueryParams> = {};
    for (const key in params) {
      if (params[key]) {
        filteredParams[key] = params[key];
      }
    }
    const qs = queryString.stringify(filteredParams);
    if (!qs) {
      return baseURL;
    }
    return `?${qs}`;
  }

  return {
    api,
    delete: _delete,
    retrieve,
    update,
    create,
    searchUrl,
  }
}
