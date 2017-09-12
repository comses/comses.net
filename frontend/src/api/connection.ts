import axios, {AxiosRequestConfig} from 'axios'
import * as _ from 'lodash'
import {CreateOrUpdateHandler} from './handler'
import * as yup from "yup";

export function getCookie(name) {
    let cookieValue: null | string = null;
    if (document.cookie && document.cookie != '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = _.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

export class Api {
    axios: any;

    constructor(config?: AxiosRequestConfig) {
        if (_.isUndefined(config)) {
            config = {
                headers: {'Content-Type': 'application/json'},
                baseURL: __BASE_URL__
            };
        }
        this.axios = axios.create(config);
        this.axios.interceptors.request.use(config => {
            config.headers['X-CSRFToken'] = getCookie('csrftoken');
            return config;
        }, error => Promise.reject(error));
    }

    async postForm(url: string, formData: FormData, config?: AxiosRequestConfig) {
        return this.axios.post(url, formData, config);
    }

    async postOrPut(method: 'post' | 'put', url: string, component: CreateOrUpdateHandler, config?: AxiosRequestConfig) {
        try {
            const response = await this.axios({method, url, data: component.state, config});
            component.handleSuccessWithDataResponse(response);
        } catch (error) {
            if (error.response.status === 400) {
                component.handleServerValidationError(error);
            } else {
                component.handleOtherError(error);
            }
        }
    }

    post(url: string, component: CreateOrUpdateHandler, config?: AxiosRequestConfig) {
        return this.postOrPut('post', url, component, config);
    }

    put(url: string, component: CreateOrUpdateHandler, config?: AxiosRequestConfig) {
        return this.postOrPut('put', url, component, config);
    }

    get(url: string, config?: AxiosRequestConfig) {
        return this.axios.get(url, config);
    }

    delete(url: string, config?: AxiosRequestConfig) {
        return this.axios.delete(url);
    }
}

export const api = new Api();