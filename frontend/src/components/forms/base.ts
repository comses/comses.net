import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'
import {Component, Prop} from 'vue-property-decorator'
import * as _ from 'lodash'

Vue.use(VeeValidate);

@Component
class BaseControl extends Vue {
    @Prop
    value;

    @Prop
    name;

    @Prop
    server_errors: Array<string>;

    get hasDanger() {
        let self: any = this;
        return self.errors.any();
    }

    get errorMessage() {
        let self: any = this;
        return self.errors.all().join(', ');
    }

    updateValue(value: string) {
        this.$emit('input', value);
    }
}

export default BaseControl;