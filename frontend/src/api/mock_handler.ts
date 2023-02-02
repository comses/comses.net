import { CreateOrUpdateHandler, FormComponent } from "./handler";
import { AxiosResponse } from "axios";
export { DismissOnSuccessHandler } from "./handler";

export class HandlerWithRedirect implements CreateOrUpdateHandler {
  constructor(public component: FormComponent, public modelId?: string) {}

  get state() {
    return this.component.state;
  }

  public handleOtherError(response_or_network_error) {
    throw response_or_network_error;
  }

  public handleServerValidationError(responseError) {
    throw responseError.response.data;
  }

  public handleSuccessWithDataResponse(response: AxiosResponse) {
    this.component.state = response.data;
  }

  public handleSuccessWithoutDataResponse(response: AxiosResponse) {
    this.component.state = response.data;
  }
}

export const HandlerShowSuccessMessage = HandlerWithRedirect;
