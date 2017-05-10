import axios from 'axios'
import {AxiosResponse} from "axios";
import * as _ from 'lodash'
import * as queryString from 'query-string'

function getCookie(name) {
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

const api_base = axios.create();
api_base.interceptors.request.use(config => {
    config.headers['X-CSRFToken'] = getCookie('csrftoken');
    return config;
}, error => Promise.reject(error));

function isAxiosResponse(response: any): response is AxiosResponse {
    return response !== undefined && (<AxiosResponse>response).status !== undefined;
}

class DrfSuccess {
    constructor(public payload: any) {
        this.kind = 'state';
    }

    kind: 'state';
}

class DrfValidationError {
    constructor(public payload: any) {
        this.kind = 'validation_error';
    }

    kind: 'validation_error';
}

type DrfResponse = DrfSuccess | DrfValidationError;

class Viewset {
    // Note: should perform schema validation here

    constructor(name: string) {
        this.name = name;
    }

    name: string;

    list(query: object = {}) {
        // 200 OK
        const qs = query === {} ? `?${queryString.stringify(query)}` : '';
        return api_base.get(`/${this.name}/${qs}`).then(response => response.data);
    }

    retrieve(id) {
        // 200 OK contains the object
        // 400 Bad Request contains validation errors
        return api_base.get(`/${this.name}/${id}/`).then(response => response.data);
    }

    create(payload): Promise<DrfResponse> {
        // 201 Created
        // 400 Bad Request contains validation errors
        return api_base.post(`/${this.name}/`, payload).then(
            (response: AxiosResponse) => new DrfSuccess(response.data),
            err => {
                console.log({err});
                if (isAxiosResponse(err.response)) {
                    return Promise.resolve(new DrfValidationError(err.response.data));
                } else {
                    return Promise.reject(err);
                }
            });
    }

    update(id, payload): Promise<DrfResponse> {
        // 200 OK
        return api_base.put(`/${this.name}/${id}/`, payload).then(
            (response: AxiosResponse) => new DrfSuccess(response.data),
            err => {
                console.log({err});
                if (isAxiosResponse(err.response)) {
                    return Promise.resolve(new DrfValidationError(err.response.data));
                } else {
                    return Promise.reject(err);
                }
            });
    }
}

export const api = {
    jobs: new Viewset('jobs'),
    events: new Viewset('events'),
    tags: new Viewset('tags')
};