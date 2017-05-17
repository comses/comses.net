<template>
    <div :class="['form-group', {'has-danger': hasDanger }]">
        <slot name="label"></slot>
        <input class="form-control" v-model="potential_degree" @keyup.enter="create" placeholder="Add degree">
        <draggable :list="value" @start="drag=true" @end="drag=false">
            <div v-for="(degree, index) in value" :key="index" class="input-group">
                <input :value="degree" @input="$emit('modify', { index, value: $event.target.value})" class="form-control">
                <button type="button" class="input-group-addon" tabindex="-1" @click="$emit('remove', index)">Delete</button>
            </div>
        </draggable>
        <div class="form-control-feedback form-control-danger">
            {{ errorMessage }}
        </div>
        <slot name="help"></slot>
    </div>
</template>
<script lang="ts">
import { Component, Prop } from 'vue-property-decorator'
import BaseControl from 'components/forms/base'
import * as draggable from 'vuedraggable'

@Component({
    components: { draggable },
    directives: {
        focus: {
            inserted(el) {
                el.focus();
            }
        }
    }
})
export default class EditDegrees extends BaseControl {
    drag: boolean = false;
    potential_degree: string = '';

    create() {
        this.$emit('create', this.potential_degree);
        this.potential_degree = '';
    }
}
</script>
