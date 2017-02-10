<template>
    <div :class="['form-group', hasDanger]">
        <label class="form-control-label">{{ label }}</label>
        <textarea :class="['form-control', formControlDanger]" :rows="rows"
                  v-on:input="updateValue($event.target.value)" v-bind:value="value"></textarea>
        <div v-if="errors.length > 0" class="form-control-feedback">{{ errorMessage }}</div>
        <small v-if="help" class="text-muted">{{ help }}</small>
    </div>
</template>
<script lang="ts">
    import { Component, Prop } from 'vue-property-decorator'
    import BaseControl from './base'

    @Component
    export default class TextArea extends BaseControl {
        @Prop
        type: string;

        @Prop
        label: string;

        @Prop({ default: 10})
        rows: string;
    }
</script>