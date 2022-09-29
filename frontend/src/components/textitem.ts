import {Component, Prop} from 'vue-property-decorator';
import BaseControl from '@/components/forms/base';
import draggable from 'vuedraggable';

@Component({
    template: `<div class="form-group">
        <slot name="label" :label="label">
            <label :class="['form-control-label', requiredClass]">{{ label }}</label>
        </slot>
        <input :class="['form-control', {'is-invalid': isInvalid}]" v-model="candidateItem" @keyup.enter="create" :placeholder="placeholder">
        <draggable :list="value" @start="drag=true" @end="drag=false">
            <div v-for="(item, index) in value" :key="index" class="input-group my-1">
                <input :value="item" @input="$emit('modify', { index, value: $event.target.value})" class="form-control">
                <button type="button" class="btn btn-delete-item" tabindex="-1" @click="$emit('remove', index)">&times;</button>
            </div>
        </draggable>
        <div v-if="isInvalid" class="invalid-feedback">
            {{ errorMessage }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
    components: {draggable},
})
export default class EditTextList extends BaseControl {
    @Prop({default: 'Press enter to add item'})
    public placeholder: string;

    @Prop()
    public label: string;

    @Prop()
    public help: string;

    public drag: boolean = false;
    public candidateItem: string = '';

    public create() {
        this.$emit('create', this.candidateItem);
        this.candidateItem = '';
    }
}
