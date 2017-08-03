<template>
    <div :class="['form-group', {'has-danger': hasDanger}]">
        <slot name="label" :label="label">
            <label class="form-control-label">{{ label }}</label>
        </slot>
        <textarea class="form-control" :name="name" :rows="rows"
                  @input="updateValue($event.target.value)" :value="value"></textarea>
        <div class="form-control-feedback form-control-danger">{{ errorMessage }}</div>
        <slot name="help"></slot>
    </div>
</template>
<script lang="ts">
    import {Component, Prop} from 'vue-property-decorator'
    import BaseControl from './base'

    @Component
    export default class TextArea extends BaseControl {
        @Prop({default: ''})
        label: string;

        @Prop({default: 10})
        rows: string;
    }
</script>