import axios from 'axios'
import {AxiosResponse} from "axios";
import * as _ from 'lodash'

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


export const api = axios.create();
api.interceptors.request.use(config => {
    config.headers['X-CSRFToken'] = getCookie('csrftoken');
    return config;
}, error => Promise.reject(error));


const handle_error =
    (reactions: {
        validation_error: (data: {non_field_errors?: Array<string>}, fail_message: string) => void,
        network_error: (fail_message: string) => void,
        other_error: (fail_message: string) => void
    }, fail_message: string) => (result) => {

        if (!result.response) {
            reactions.network_error(result.message || 'NetworkError: ' + fail_message)
        } else {
            const response = result.response;
            const content_type = response.headers['content-type'];
            const status = response.status;
            if (status === 400 && content_type === 'application/json') {
                reactions.validation_error(response.data, 'ValidationError: ' + fail_message)
            } else {
                reactions.other_error('OtherError: ' + fail_message);
            }
        }
        return result;
    };

const handle_network_error = (page: any) => (fail_message: string): void => {
    page.main_error = fail_message;
};

const handle_validation_error = (page: any) => (data: {non_field_errors?: Array<string>}, fail_message: string): void => {
    page.main_error = data.non_field_errors || fail_message;
    page.validation_errors = data;
};

const handle_other_error = handle_network_error;

export const default_handle_error = (page: any) => handle_error({
    validation_error: handle_validation_error(page),
    network_error: handle_network_error(page),
    other_error: handle_other_error(page)
}, 'Unknown error occurred');

// 400 -> ValidationError
// Other 400

function delete_record(url: string) {
    return api.delete(url);
}

function update_record<T>(url: string, payload: T) {
    return api.put(url, payload);
}

function create_record<T>(url: string, payload: T) {
    return api.post(url, payload);
}