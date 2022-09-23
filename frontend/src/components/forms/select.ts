// TODO: consider refactoring form components to .vue SFCs
import { Component, Prop, ModelSync } from 'vue-property-decorator';
import BaseControl from './base';

// FIXME: redo custom input
@Component({
    template: `<div class="form-group">
        <slot name="label">
            <label :for='controlId' :class="['form-control-label', requiredClass]">{{ label }}</label>
        </slot>
        <select :id='controlId' :name="name" :class="['form-control', {'is-invalid': isInvalid}]" 
                @change="updateValue($event.target.value)" v-model="selectedLocal">
            <option :value="option.value" :selected="option.value === selectedOption" v-for="option in options">
                {{ option.label }}
            </option>
        </select>
        <div v-if="customSelected()">
            <label for="inputCustom" class="form-label"></label>
            <input :value="value" class="form-control" :id="customInputId" :placeholder="customPlaceholder"
            @input="updateValue($event.target.value)"/>
        </div>
        <div class="invalid-feedback">
            {{ errorMessage }}
        </div>
        <slot name="help">
            <small :aria-describedby='controlId' class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`, 
})
class Select extends BaseControl {
    @Prop({default: ''})
    public validate: string;

    @Prop({default: ''})
    public label: string;

    @Prop({default: ''})
    public help: string;

    @Prop()
    public options: [{value: string, label: string}];

    @Prop({default: null})
    public customOption: string | null;

    @Prop({default: ''})
    public customPlaceholder: string;

    @Prop({default: '' })
    public selectedOption: string;

    @ModelSync('selectedOption', 'input', { type: String })
    readonly selectedLocal!: string;

    get customInputId() {
        return `${this.name}CustomInput`;
    }

    public created() {
        this.setSelectedOption();
    }

    public updated() {
        if (this.value === this.customOption) {
            this.selectInputText();
        }
    }

    public selectInputText() {
        const input = document.getElementById(this.customInputId) as HTMLInputElement;
        input.focus();
        input.select();
    }

    public setSelectedOption() {
        if (this.value) {
            this.selectedOption = this.value;
        }
    }

    public customSelected() {
        return (this.customOption === this.selectedOption);
    }
}

export default Select;
