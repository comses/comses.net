import {AxiosRequestConfig, AxiosResponse} from 'axios'
import * as _ from 'lodash'
import * as _$ from 'jquery'
import axios from "axios";

const $: any = _$;

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

enum StatusMessageCode {
    danger,
    warning,
    success
}

function changePage(url: string) {
    window.location.href = url;
}

export interface CreateOrUpdateHandler {
    state: object

    handleSuccessWithDataResponse(response: AxiosResponse): void

    handleSuccessWithoutDataResponse(response: AxiosResponse): void

    handleOtherError(network_error): void

    handleServerValidationError(response: { response: AxiosResponse }): void
}

export interface FormComponent {
    validate(): Promise<any>

    state: object
    statusMessages: Array<{ classNames: string, message: string }>
    $emit: (...x: Array<any>) => void
}

export interface FormRedirectComponent extends FormComponent {
    errors

    detailPageUrl(state): string
}

function baseHandleOtherError(response_or_network_error): string {
    let msg: string;
    if (!_.isUndefined(response_or_network_error.response)) {
        switch (response_or_network_error.response.status) {
            case 403: msg = 'Server Forbidden Error (tried to read, create or modify something you do not have permission to)'; break;
            case 404: msg = 'Server Resource Not Found Error (tried to read, create or modify something that does not exist)'; break;
            case 500: msg = 'Internal Server Error (server has a bug)'; break;
            default: msg = `HTTP Error (${response_or_network_error.response.status})`; break;
        }
    } else {
        msg = 'Network Error. Request never got a response from server.'
    }
    return msg;
}

function baseHandleValidationError(responseError, component: FormRedirectComponent) {
    const response = responseError.response;
    component.statusMessages = [{classNames: 'alert alert-danger', message: 'Server side validation failed'}];
    const non_field_errors = response.data.non_field_errors;
    for (const field of _.keys(response.data)) {
        if (!_.isUndefined(component.errors[field])) {
            component.errors[field] = response.data[field];
        } else {
            component.statusMessages.push({
                classNames: 'alert alert-danger',
                message: `${field}: '${response.data[field]}'`
            })
        }
    }
}

export class HandlerWithRedirect implements CreateOrUpdateHandler {
    // Requires state and detailPageUrl properties to be present on component

    constructor(public component: FormRedirectComponent) {
    }

    get state() {
        return this.component.state;
    }

    handleOtherError(response_or_network_error) {
        const msg = baseHandleOtherError(response_or_network_error);
        this.component.statusMessages = [{classNames: 'alert alert-danger', message: msg}];
    }


    handleServerValidationError(responseError) {
        baseHandleValidationError(responseError, this.component);
    }

    handleSuccessWithDataResponse(response: AxiosResponse) {
        changePage(this.component.detailPageUrl(response.data));
    }

    handleSuccessWithoutDataResponse(response: AxiosResponse) {
        changePage(this.component.detailPageUrl(response.data));
    }
}

export class HandlerShowSuccessMessage implements CreateOrUpdateHandler {
    constructor(public component: FormComponent) {
    }

    get state() {
        return this.component.state;
    }

    handleOtherError(response_or_network_error) {
        const msg = baseHandleOtherError(response_or_network_error);
        this.component.statusMessages = [{classNames: 'alert alert-danger', message: msg}];
    }

    handleServerValidationError(response: { response: AxiosResponse}) {
        const message = response.response.data.non_field_errors;
        this.component.statusMessages = [{
            classNames: 'alert alert-danger',
            message: message ? `Server side validation failed: ${message}` : 'Server side validation failed'
        }];
    }

    handleSuccessWithDataResponse(response: AxiosResponse) {
        this.component.state = response.data;
        this.component.statusMessages = [{classNames: 'alert alert-success', message: 'Successfully saved'}];
    }

    handleSuccessWithoutDataResponse(response: AxiosResponse) {
        this.component.statusMessages = [{classNames: 'alert alert-success', message: 'Successfully saved'}];
    }


}

export class DismissOnSuccessHandler implements CreateOrUpdateHandler {
    constructor(public component: FormComponent, public modalId: string) {
    }

    get state() {
        return this.component.state;
    }

    handleOtherError(response_or_network_error) {
        let msg;
        if (!_.isUndefined(response_or_network_error.response)) {
            switch (response_or_network_error.response.status) {
                case 403: msg = 'Server Forbidden Error (tried to readm create or modify something you do not have permission to)'; break;
                case 404: msg = 'Server Resource Not Found Error (tried to read, create or modify something that does not exist)'; break;
                case 500: msg = 'Internal Server Error (server has a bug)'; break;
                default: msg = `HTTP Error (${response_or_network_error.response.status})`; break;
            }
        } else {
            msg = 'Network Error. Request never got a response from server.'
        }

        this.component.statusMessages = [{classNames: 'alert alert-danger', message: msg}];
    }

    handleServerValidationError(response: { response: AxiosResponse }) {
        this.component.statusMessages = [{classNames: 'alert alert-danger', message: 'Server side validation failed'}];
    }

    handleSuccessWithDataResponse(response: AxiosResponse) {
        this.component.state = response.data;
        this.component.statusMessages = [];
        this.dismissModal();
    }

    handleSuccessWithoutDataResponse(response: AxiosResponse) {
        this.component.statusMessages = [];
        this.dismissModal();
    }

    dismissModal() {
        $(this.modalId).modal('hide');
        this.component.$emit('updated', this.state);
    }
}

export class Api {
    public axios: any;

    constructor(config?: AxiosRequestConfig) {
        if (_.isUndefined(config)) {
            config = {
                headers: {'Content-Type': 'application/json'},
                baseURL: (<any>window).__BASE_URL__
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
