import SearchForm from 'components/search_form.vue'
import Input from 'components/forms/input.vue'
import * as Vue from 'vue'
import {ScopedSlot} from "vue/types/vnode";

new SearchForm({propsData: {model_name: 'Event'}}).$mount('#app');