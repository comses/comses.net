import EditJob from './edit.vue'
import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'

Vue.use(VeeValidate);

const job = new EditJob().$mount('#app');