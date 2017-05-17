// import EditProfile from './edit.vue'
import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'

Vue.use(VeeValidate);


declare const require: {
    <T>(path: string): T;
    (paths: string[], callback: (...modules: any[]) => void): void;
    ensure: (paths: string[], callback: (require: <T>(path: string) => T) => void) => void;
};

require('expose-loader?EditProfile!./edit.vue');