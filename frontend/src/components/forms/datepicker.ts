
import {Component, Prop} from 'vue-property-decorator'
import BaseControl from './base'
import * as Datepicker from 'vuejs-datepicker'

@Component({
    template: `<div class="form-group">
        <slot name="label"></slot>
        <datepicker :value="dateValue" @input="updateDate" wrapper-class="input-group"
                    :input-class="datepickerInputClass" :clear-button="clearButton" @cleared="cleared">
        </datepicker>
        <div v-if="isInvalid" class="invalid-feedback-always">{{ errorMessage }}</div>
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

    get dateValue() {
        // Otherwise displayed date is off by one https://github.com/charliekassel/vuejs-datepicker/issues/158
        const [yearStr, monthStr, dayStr] = this.value.split('-');
        const year = parseInt(yearStr);
        const month = parseInt(monthStr) - 1; // month argument is zero indexed so 0 is January
        const day = parseInt(dayStr.split('T')[0]);
        return new Date(year, month, day);
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