import * as Vue from 'vue'
import {Component, Prop} from 'vue-property-decorator'

@Component
class BaseControl extends Vue {
    @Prop
    errors: Array<string>;

    @Prop
    value;

    @Prop({default: ''})
    help: string;

    get errorMessage() {
        return this.errors.join('. ');
    }

    get hasDanger() {
        return {
            'has-danger': this.errors.length > 0
        };
    }

    get formControlDanger() {
        return {
            'form-control-danger': this.errors.length > 0
        };
    }

    updateValue(value) {
        this.$emit('input', value);
    }
}

export default BaseControl;