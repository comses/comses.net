import {Api} from './handler';
import {__TEST_USERNAME__, __TEST_USER_PASSWORD__} from '../__config__/common';

export const api = new Api({
    headers: {'Content-Type': 'application/json'},
    auth: {username: __TEST_USERNAME__, password: __TEST_USER_PASSWORD__},
});
