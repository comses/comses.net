import { Component, Prop } from 'vue-property-decorator'
import BaseControl from './base'

@Component({
    template: `<div :class="['form-group', {'has-danger': hasDanger }]">
        <slot name="label" :label="label">
            <label class="form-control-label">{{ label }}</label>
        </slot>
        <input :type="type" :name="name" class="form-control" :value="value"
                @change="toggle($event.target.value)" v-if="type === 'checkbox'">
        <input :type="type" :name="name" class="form-control" :value="value"
                @input="updateValue($event.target.value)" v-else>
        <div class="form-control-feedback form-control-danger">
            {{ errorMessage }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`
})
class Input extends BaseControl {
    @Prop({ default: ''})
    validate: string;

    @Prop({ default: 'text'})
    type: string;

    @Prop({default: ''})
    label: string;

    @Prop({ default: ''})
    help: string;

    toggle(value: string) {
        let v: boolean = false;
        if (value === 'true') {
            v = true
        }
        this.$emit('input', !v);
    }
}

export default Input;