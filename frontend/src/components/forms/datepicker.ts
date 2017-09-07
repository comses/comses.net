
import {Component, Prop} from 'vue-property-decorator'
import BaseControl from './base'
import * as Datepicker from 'vuejs-datepicker'

@Component({
    template: `<div class="form-group">
        <slot name="label"></slot>
        <datepicker :value="value" @input="updateDate" wrapper-class="input-group"
                    :input-class="datepickerInputClass" :clear-button="clearButton" @cleared="cleared">
        </datepicker>
        <div v-if="isInvalid" class="invalid-feedback">{{ errorMessage }}</div>
        <slot name="help"></slot>
    </div>`,
    components: {
        'datepicker': Datepicker
    }
})
export default class InputDatepicker extends BaseControl {
    @Prop({default: false})
    clearButton: boolean;

    get datepickerInputClass() {
        return this.isInvalid ? 'form-control is-invalid' : 'form-control';
    }

    updateDate(value) {
        switch (value.constructor.name) {
            case 'String': this.updateValue(value); break;
            case 'Date': this.updateValue(value.toISOString()); break;
            default: throw Error(`invalid type ${value.constructor.name} in date field`);
        }
    }

    cleared() {
        this.updateValue(null);
    }
}