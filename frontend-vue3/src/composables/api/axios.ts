import { reactive } from "vue";
import axios, { AxiosError, type AxiosRequestConfig } from "axios";
import queryString from "query-string";

interface AxiosRequestState {
  response: any;
  data: any;
  error: any;
  isLoading: boolean;
  isFinished: boolean;
}

export function useAxios(baseUrl?: string, config?: AxiosRequestConfig) {
  const instance = axios.create({
    headers: { "Content-Type": "application/json" },
    baseURL: window.location.origin,
    ...config,
  });

  instance.interceptors.request.use(
    config => {
      const csrfToken = getCookie("csrftoken");
      if (csrfToken) {
        config.headers["X-CSRFToken"] = csrfToken;
      }
      return config;
    },
    error => Promise.reject(error)
  );

  const state = reactive<AxiosRequestState>({
    response: null,
    data: undefined,
    error: null,
    isLoading: false,
    isFinished: false,
  });

  async function request(url: string, method: string, data: any, config?: AxiosRequestConfig) {
    state.isLoading = true;
    try {
      const response = await instance({ url, method, data, ...config });
      state.response = response;
      state.data = response.data;
      state.error = null;
      state.isFinished = true;
      return response;
    } catch (error: unknown) {
      state.error = error;
      if (error instanceof AxiosError && error.response) {
        state.response = error.response;
        state.isFinished = true;
        return error.response;
      }
      state.isFinished = true;
      throw error;
    } finally {
      state.isLoading = false;
    }
  }

  async function get(url: string, config?: AxiosRequestConfig) {
    return request(url, "GET", null, config);
  }

  async function post(url: string, data?: any, config?: AxiosRequestConfig) {
    return request(url, "POST", data, config);
  }

  async function postForm(url: string, formData: FormData, config?: AxiosRequestConfig) {
    return request(url, "POST", formData, config);
  }

  async function put(url: string, data: any, config?: AxiosRequestConfig) {
    return request(url, "PUT", data, config);
  }

  async function del(url: string, config?: AxiosRequestConfig) {
    return request(url, "DELETE", null, config);
  }

  function detailUrl(id: string | number) {
    return `${baseUrl}${id}/`;
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
      return baseUrl || window.location.origin;
    }
    return `${baseUrl}?${qs}`;
  }

  return {
    instance,
    state,
    get,
    post,
    postForm,
    put,
    del,
    detailUrl,
    searchUrl,
  };
}

function getCookie(name: string) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
