import {CreateOrUpdateHandler, FormRedirectComponent} from "./handler";
import {AxiosResponse} from "axios";

export class HandlerWithRedirect implements CreateOrUpdateHandler {
        constructor(public component: FormRedirectComponent, public modelId?: string) {
    }

    get state() {
        return this.component.state;
    }

    handleOtherError(response_or_network_error) {
        console.error(response_or_network_error);
    }

    handleServerValidationError(responseError) {
        console.error(responseError);
    }

    handleSuccessWithDataResponse(response: AxiosResponse) {
        this.component.state = response.data;
    }

    handleSuccessWithoutDataResponse(response: AxiosResponse) {
        this.component.state = response.data;
    }
}

export const HandlerShowSuccessMessage = HandlerWithRedirect;