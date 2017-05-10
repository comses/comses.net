import SearchForm from 'components/sidebar.vue'
import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'

Vue.use(VeeValidate);

new SearchForm().$mount('#sidebar');