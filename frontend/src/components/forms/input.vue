<template>
    <div :class="['form-group', {'has-danger': hasDanger }]">
        <slot name="label"></slot>
        <input :type="type" :name="name" class="form-control" :value="value" v-validate="validate"
               @input="updateValue($event.target.value)">
        <div class="form-control-feedback form-control-danger">
            {{ errorMessage }}
        </div>
        <slot name="help"></slot>
    </div>
</template>
<script lang="ts">
    import { Component, Prop } from 'vue-property-decorator'
    import BaseControl from './base'

    @Component
    export default class Input extends BaseControl {
        @Prop({ default: ''})
        validate: string;

        @Prop({ default: 'text'})
        type: string;
    }
</script>