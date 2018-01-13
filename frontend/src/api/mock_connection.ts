import {Api} from './handler'
import {__BASIC_AUTH_PASSWORD__, __BASIC_AUTH_USERNAME__} from "../__config__/common";

export const api = new Api({
    headers: {'Content-Type': 'application/json'},
    auth: {username: __BASIC_AUTH_USERNAME__, password: __BASIC_AUTH_PASSWORD__}
});