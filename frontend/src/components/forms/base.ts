import * as Vue from 'vue'
import {Component, Prop} from 'vue-property-decorator'

@Component
class BaseControl extends Vue {
    @Prop
    value: { value, errors: Array<string> };

    get hasErrors() {
        return this.value.errors.length > 0;
    }

    get errorMessage() {
        console.log(this.value.errors);
        return this.value.errors.join('. ');
    }

    get hasDanger() {
        return {
            'has-danger': this.hasErrors
        };
    }

    get formControlDanger() {
        return {
            'form-control-danger': this.hasErrors
        };
    }

    updateValue(value) {
        this.$emit('input', {value, errors: this.value.errors});
    }
}

export default BaseControl;