import { Component } from 'vue-property-decorator';
import Vue from 'vue';

@Component({
  template: `<div>
    {{ state }}
  </div>`
})
class Other extends Vue {
  data() {
    return {
      state: 'Hello World!'
    };
  }
}

new Other().$mount('#app');
