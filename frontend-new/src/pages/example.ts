import { Vue } from 'vue-property-decorator'
import Example from './Example.vue'

new Vue({
  render: (h) => h(Example),
}).$mount('#app');
