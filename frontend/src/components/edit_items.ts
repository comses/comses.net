import { Component, Prop } from 'vue-property-decorator'
import BaseControl from 'components/forms/base'
import * as draggable from 'vuedraggable'

@Component({
    template: `<div :class="['form-group', {'has-danger': hasDanger }]">
        <slot name="label"></slot>
        <input class="form-control" v-model="potential_item" @keyup.enter="create" :placeholder="placeholder">
        <draggable :list="value" @start="drag=true" @end="drag=false">
            <div v-for="(item, index) in value" :key="index" class="input-group">
                <input :value="item" @input="$emit('modify', { index, value: $event.target.value})" class="form-control">
                <button type="button" class="input-group-addon" tabindex="-1" @click="$emit('remove', index)">Delete</button>
            </div>
        </draggable>
        <div class="form-control-feedback form-control-danger">
            {{ errorMessage }}
        </div>
        <slot name="help"></slot>
</div>`,
    components: { draggable }
})
export default class EditTextList extends BaseControl {
    @Prop({ default: 'Add item'})
    placeholder: string;

    drag: boolean = false;
    potential_item: string = '';

    create() {
        this.$emit('create', this.potential_item);
        this.potential_item = '';
    }
}
