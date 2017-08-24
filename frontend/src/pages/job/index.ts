import EditJob from './edit'
import * as Vue from 'vue'

function matchUpdateUrl(pathname) {
    let match = pathname.match(/\/jobs\/([0-9]+)\/edit\//);
    if (match !== null) {
        match = match[1];
    }
    return match
}

const id = matchUpdateUrl(window.location.pathname);

const job = new EditJob({ propsData: { id }}).$mount('#app');