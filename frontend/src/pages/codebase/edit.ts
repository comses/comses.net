import EditEvent from './edit.vue'
import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'

Vue.use(VeeValidate);
new EditEvent().$mount('#app');