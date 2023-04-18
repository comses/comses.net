import { reactive } from "vue";
import axios, { AxiosError, type AxiosRequestConfig, type AxiosResponse } from "axios";
import queryString from "query-string";

export interface AxiosRequestState {
  response: any;
  data: any;
  serverErrors: string[];
  isLoading: boolean;
  isFinished: boolean;
}

export interface RequestOptions {
  config?: AxiosRequestConfig;
  onSuccess?: (response: AxiosResponse) => void;
  onError?: (error: AxiosError) => void;
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
    serverErrors: [],
    isLoading: false,
    isFinished: false,
  });

  async function request(url: string, method: string, data: any, options: RequestOptions = {}) {
    const { config, onSuccess, onError } = options;
    state.isLoading = true;
    try {
      const response = await instance({ url, method, data, ...config });
      state.response = response;
      state.data = response.data;
      state.isFinished = true;
      if (onSuccess) {
        onSuccess(response);
      }
      return response;
    } catch (error: unknown) {
      if (error instanceof AxiosError && error.response) {
        state.response = error.response;
        state.isFinished = true;
        if (onError) {
          onError(error);
        }
        if (error.response.status === 400) {
          state.serverErrors = describeValidationError(error.response);
        } else {
          state.serverErrors = describeNonValidationError(error.response);
        }
        return error.response;
      } else {
        state.serverErrors.push("An unexpected error occurred.");
      }
      state.isFinished = true;
      throw error;
    } finally {
      state.isLoading = false;
    }
  }

  async function get(url: string, options?: RequestOptions) {
    return request(url, "GET", null, options);
  }

  async function post(url: string, data?: any, options?: RequestOptions) {
    return request(url, "POST", data, options);
  }

  async function postForm(url: string, formData: FormData, options?: RequestOptions) {
    return request(url, "POST", formData, options);
  }

  async function put(url: string, data: any, options?: RequestOptions) {
    return request(url, "PUT", data, options);
  }

  async function del(url: string, options?: RequestOptions) {
    return request(url, "DELETE", null, options);
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

function describeNonValidationError(errorResponse: AxiosResponse): string[] {
  switch (errorResponse.status) {
    case 403:
      return [
        "Server Forbidden Error (tried to read, create or modify something you do not have permission to)",
      ];
    case 404:
      return [
        "Server Resource Not Found Error (tried to read, create or modify something that does not exist)",
      ];
    case 500:
      return ["Internal Server Error (server has a bug)"];
    default:
      return [`HTTP Error (${errorResponse.status})`];
  }
}

function describeValidationError(errorResponse: AxiosResponse): string[] {
  const errors = [];
  for (const e in errorResponse.data) {
    if (e === "non_field_errors") {
      errors.push(...errorResponse.data[e]);
    } else {
      errors.push(`${e}: ${errorResponse.data[e].join(", ")}`);
    }
  }
  return errors;
}

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
