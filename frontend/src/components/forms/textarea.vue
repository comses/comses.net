<template>
    <div :class="['form-group', {'has-danger': hasDanger}]">
        <slot name="label"></slot>
        <textarea :class="['form-control', {'form-control-danger': hasDanger}]" :rows="rows" v-validate="validate"
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
        validate: string;

        @Prop({default: 10})
        rows: string;
    }
</script>