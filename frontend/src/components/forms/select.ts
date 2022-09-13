// TODO: consider refactoring form components to .vue SFCs
import { Component, Prop } from 'vue-property-decorator';
import BaseControl from './base';

@Component({
    template: `<div class="form-group">
        <slot name="label">
            <label :for='controlId' :class="['form-control-label', requiredClass]">{{ label }}</label>
        </slot>
        <select :id='controlId' :name="name" :class="['form-control', {'is-invalid': isInvalid}]" 
                :value="value" @change="updateValue($event.target.value)" v-model="selectedOption">
            <option :value="option" :selected="option === selectedOption" v-for="option in options">
                {{ option }}
            </option>
        </select>
        <div v-if="customSelected()">
            <label for="inputCustom" class="form-label"></label>
            <input :value="value" class="form-control" id="inputCustom" :placeholder="customPlaceholder"
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
    @Prop({ default: ''})
    public validate: string;

    @Prop({default: ''})
    public label: string;

    @Prop({ default: ''})
    public help: string;

    @Prop({ default: ['']})
    public options: string[];

    @Prop({ default: null})
    public customOption: string | null;

    @Prop({ default: ''})
    public customPlaceholder: string;

    public selectedOption = '';

    public created() {
        this.setSelectedOption();
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
