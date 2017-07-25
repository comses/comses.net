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

    @Prop({default: () => []})
    errorMsgs: Array<string>;

    get hasDanger() {
        return this.errorMsgs.length > 0;
    }

    get errorMessage() {
        return this.errorMsgs.join(', ');
    }

    updateValue(value: string) {
        this.$emit('input', value);
    }
}

export default BaseControl;