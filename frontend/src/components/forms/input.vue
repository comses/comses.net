<template>
    <div :class="['form-group', hasDanger]">
        <slot name="label"></slot>
        <input :type="type" :class="['form-control', formControlDanger]"
               @input="updateValue($event.target.value)"
               :value="value.value">
        <div v-if="hasErrors" class="form-control-feedback">{{ errorMessage }}</div>
        <slot name="help"></slot>
    </div>
</template>
<script lang="ts">
    import { Component, Prop } from 'vue-property-decorator'
    import BaseControl from './base'

    @Component
    export default class Input extends BaseControl {
        @Prop
        type: string;
    }
</script>