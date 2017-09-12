import axios from 'axios'
import {__BASIC_AUTH_USERNAME__, __BASIC_AUTH_PASSWORD__} from "./common"
import * as _ from 'lodash'
import {Api} from 'api/connection'

function getCookie(name) {
    let cookieValue: string | null = null;
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

const api = new Api({
    headers: {'Content-Type': 'application/json'},
    auth: {username: __BASIC_AUTH_USERNAME__, password: __BASIC_AUTH_PASSWORD__}
});

jest.mock('api/connection',
    () => ({api})
);