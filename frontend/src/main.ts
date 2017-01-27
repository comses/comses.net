import * as Vue from 'vue';

import store from './store/index'
import router from './router-config'

import './components/ClassComponentsHooks'
import { sync } from 'vuex-router-sync';

import App from './App.vue'

sync(store, router);

const app = new Vue({
    router,
    store,
    render: h => h(App)
}).$mount("#app");