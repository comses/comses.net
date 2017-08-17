import EditEvent from './edit'
import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'

Vue.use(VeeValidate);

function matchUpdateUrl(pathname) {
    let match = pathname.match(/\/events\/([0-9]+)\/update\//);
    if (match !== null) {
        match = match[1];
    }
    return match
}

const id = matchUpdateUrl(document.location.pathname);
new EditEvent({ propsData: {id}}).$mount('#app');