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
  /**
   * Composable API for making requests with axios
   *
   * @param baseUrl - Base URL for API requests. Optional.
   * @param config - Optional axios configuration. Optional.
   * @returns - An object containing the axios instance, request state, and helper functions for API requests
   */

  const instance = axios.create({
    headers: { "Content-Type": "application/json" },
    baseURL: window.location.origin,
    ...config,
  });

  // add CSRF token to all requests
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

  // convert date strings to Date objects in response data
  instance.interceptors.response.use(
    response => {
      if (response.data) {
        convertDates(response.data);
      }
      return response;
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

/**
 * Utility functions
 */
function getCookie(name: string) {
  return document.cookie.split("; ").reduce((r, v) => {
    const [n, ...val] = v.split("=");
    return n === name ? decodeURIComponent(val.join("=")) : r;
  }, "");
}

const ISODateFormat = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d*)?(?:[-+]\d{2}:?\d{2}|Z)?$/;

function isISODateString(value: any) {
  return value && typeof value === "string" && ISODateFormat.test(value);
}

function convertDates(body: any) {
  if (body === null || body === undefined || typeof body !== "object") {
    return body;
  }
  for (const key of Object.keys(body)) {
    const value = body[key];
    if (isISODateString(value)) {
      body[key] = new Date(value);
    } else if (typeof value === "object") {
      convertDates(value);
    }
  }
}
