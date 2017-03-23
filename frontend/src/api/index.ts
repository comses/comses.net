import axios from 'axios'
import {AxiosResponse} from "axios";
import * as _ from 'lodash'
import {PageContext, ValidationErrors, PageState, Lens} from "../store/common";

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


// General error handling

const handleError =
    (reactions: {
        handleValidationErrors: (data: {non_field_errors?: Array<string>}, fail_message: string) => void,
        handleNetworkError: (fail_message: string) => void,
        handleOtherError: (fail_message: string) => void
    }, fail_message: string) => (result) => {

        if (!result.response) {
            reactions.handleNetworkError(result.message || 'NetworkError: ' + fail_message)
        } else {
            const response = result.response;
            const content_type = response.headers['content-type'];
            const status = response.status;
            if (status === 400 && content_type === 'application/json') {
                reactions.handleValidationErrors(response.data, 'ValidationError: ' + fail_message)
            } else {
                reactions.handleOtherError('OtherError: ' + fail_message);
            }
        }
        return result;
    };

const handleNetworkError = <T>(context: PageContext<T>) => (fail_message: string): void => {
    context.mainError([fail_message]);
};

const handleOtherError = handleNetworkError;

/*
 * Error handling for when the whole state is replaced
 */

const rootHandleValidationErrors = <T>(context: PageContext<T>) => (data: ValidationErrors<T>,
                                                                    fail_message: string): void => {
    context.mainError(data.non_field_errors || [fail_message]);
    delete data.non_field_errors;
    context.validationErrors(data);
};

const rootHandleError = <T>(context: PageContext<T>) => handleError({
    handleValidationErrors: rootHandleValidationErrors(context),
    handleNetworkError: handleNetworkError(context),
    handleOtherError: handleOtherError(context)
}, 'Unknown error occurred');


const rootHandleSuccess = <T>(url: string, context: PageContext<T>) => (response: AxiosResponse) => {
    context.data(response.data);
    context.validationErrors({});
    context.mainError([]);
    // window.location.href = document.referrer || url;
};


export function rootDeleteRecord<T>(context: PageContext<T>, url: string) {
    return api.delete(url).then(rootHandleSuccess(url, context), rootHandleError(context));
}

export function rootUpdateRecord<T, P>(context: PageContext<T>, url: string, payload: P) {
    return api.put(url, payload).then(rootHandleSuccess(url, context), rootHandleError(context));
}

export function rootCreateRecord<T, P>(context: PageContext<T>, url: string, payload: P) {
    return api.post(url, payload).then(rootHandleSuccess(url, context), rootHandleError(context));
}

export function rootRetrieveRecord<T>(context: PageContext<T>, url: string) {
    return api.get(url).then(rootHandleSuccess(url, context), rootHandleError(context))
}

/*
 * Nested error handling for when a subset of the state is replaced
 */

const relatedSetErrors = (errors) => (old_state) => {
    old_state.errors = errors;
    return errors
};

export const relatedTransformSuccess = <T>(data: T) => (state: { value: any }): { value: any } => {
    state.value = data;
    return state;
};

// handle errors that occur that only modify a slice of the page state
const relatedHandleError = (stateLens: Lens) => handleError({
    handleValidationErrors: (data: {non_field_errors?: Array<string>}, fail_message: string) => {
        const errors = _.map(_.values(data), el => el.toString());
        stateLens.over(relatedSetErrors(errors));
    },
    handleNetworkError: (fail_message: string) => {
        stateLens.over(relatedSetErrors([fail_message]));
    },
    handleOtherError: (fail_message: string) => {
        stateLens.over(relatedSetErrors([fail_message]));
    }
}, 'Unknown error occurred');

const relatedHandleSuccess =
    (stateLens, data_transform: <T, S>(data: T) => (state: S) => S) =>
    (response: AxiosResponse) => {
    stateLens.over(data_transform(response.data));
};

export function relatedRetrieveRecord<T, S>(stateLens, data_transform: (data: T) => (state: S) => S, url: string) {
    return api.get(url).then(
        relatedHandleSuccess(stateLens, data_transform),
        relatedHandleError(stateLens))
}

export function relatedCreateRecord<T, S, P>(stateLens, data_transform: (data: T) => (state: S) => S, url: string, payload: P) {
    return api.post(url, payload).then(
        relatedHandleSuccess(stateLens, data_transform),
        relatedHandleError(stateLens))
}

export function createDefaultState<T>(defaultValue: T) {
    let content: any = {};
    for (const k in defaultValue) {
        content[k] = { value: defaultValue[k], errors: []}
    }
    return { mainError: [], content };
}