import {Component, Prop} from 'vue-property-decorator';
import BaseControl from './base';

@Component({
    template: `<div class="form-group">
        <slot name="label" :label="label">
            <label :for='controlId' class="form-control-label">{{ label }}</label>
        </slot>
        <textarea :id='controlId' :class="['form-control', {'is-invalid': isInvalid}]" :name="name" :rows="rows"
                    @input="updateValue($event.target.value)" :value="value"></textarea>
        <div v-if="isInvalid" class="invalid-feedback">{{ errorMessage }}</div>
        <slot name="help">
            <small :aria-describedby='controlId' class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
})
export default class TextArea extends BaseControl {
    @Prop({default: ''})
    public label: string;

    @Prop({ default: ''})
    public help: string;

    @Prop({default: 10})
    public rows: string;
}
