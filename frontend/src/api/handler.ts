import {AxiosResponse} from 'axios'
import * as _ from 'lodash'

enum StatusMessageCode {
    danger,
    warning,
    success
}


function changePage(url: string) {
    window.location.href = url;
}

export interface CreateOrUpdateHandler {
    handleSuccessWithDataResponse(response: AxiosResponse): void

    handleSuccessWithoutDataResponse(response: AxiosResponse): void

    handleOtherError(network_error): void

    handleServerValidationError(response: AxiosResponse): void
}

export interface FormComponent {
    validate(): Promise<any>

    state: object
    statusMessages: Array<{ classNames: string, message: string }>
}

export interface FormRedirectComponent extends FormComponent {
    errors

    detailPageUrl(state): string
}

export class HandlerWithRedirect implements CreateOrUpdateHandler {
    // Requires state and detailPageUrl properties to be present on component

    constructor(public component: FormRedirectComponent) {
    }

    get state() {
        return this.component.state;
    }

    handleOtherError(response_or_network_error) {
        this.component.statusMessages = [{classNames: 'alert alert-danger', message: 'Network error'}];
    }

    handleServerValidationError(responseError) {
        const response = responseError.response;
        this.component.statusMessages = [{classNames: 'alert alert-danger', message: 'Server side validation failed'}];
        const non_field_errors = response.data.non_field_errors;
        for (const field of _.keys(response.data)) {
            if (!_.isUndefined(this.component.errors[field])) {
                this.component.errors[field] = response.data[field];
            } else {
                this.component.statusMessages.push({
                    classNames: 'alert alert-danger',
                    message: `${field}: '${response.data[field]}'`
                })
            }
        }
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
        this.component.statusMessages = [{classNames: 'alert alert-danger', message: 'Network error'}];
    }

    handleServerValidationError(response: AxiosResponse) {
        this.component.statusMessages = [{classNames: 'alert alert-danger', message: 'Server side validation failed'}];
    }

    handleSuccessWithDataResponse(response: AxiosResponse) {
        this.component.state = response.data;
        this.component.statusMessages = [{classNames: 'alert alert-success', message: 'Successfully saved'}];
    }

    handleSuccessWithoutDataResponse(response: AxiosResponse) {
        this.component.statusMessages = [{classNames: 'alert alert-success', message: 'Successfully saved'}];
    }
}
