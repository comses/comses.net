import EditEvent from './edit'
import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'

Vue.use(VeeValidate);
new EditEvent().$mount('#app');