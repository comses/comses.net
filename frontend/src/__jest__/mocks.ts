import axios from 'axios'
import {__BASIC_AUTH_USERNAME__, __BASIC_AUTH_PASSWORD__} from "./common"
import * as _ from 'lodash'

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

const api_base = axios.create({
    headers: {'Content-Type': 'application/json'},
    auth: {username: __BASIC_AUTH_USERNAME__, password: __BASIC_AUTH_PASSWORD__}
});
api_base.interceptors.request.use(config => {
    config.headers['X-CSRFToken'] = getCookie('csrftoken');
    return config;
}, error => Promise.reject(error));


jest.mock('api/connection',
    () => ({api_base})
);
