import axios from 'axios'
import * as _ from 'lodash'

export function getCookie(name) {
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

export const api_base = axios.create({
    headers: { 'Content-Type': 'application/json'},
});
api_base.interceptors.request.use(config => {
    config.headers['X-CSRFToken'] = getCookie('csrftoken');
    return config;
}, error => Promise.reject(error));