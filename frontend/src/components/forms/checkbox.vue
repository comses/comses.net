<template>
    <div :class="['form-check', {'has-danger': hasDanger }]">
        <label class="form-check-label">
            <input type="checkbox" :name="name" class="form-check-input" :value="value"
                   @change="toggle($event.target.value)">
            <slot name="label" :label="label">{{ label }}</slot>
        </label>
        <div class="form-control-feedback form-control-danger">
            {{ errorMessage }}
        </div>
        <slot name="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>
</template>
<script lang="ts">
    import { Component, Prop } from 'vue-property-decorator'
    import BaseControl from './base'

    @Component
    class Checkbox extends BaseControl {
        @Prop({ default: ''})
        validate: string;

        @Prop
        label: string;

        @Prop({ default: ''})
        help: string;

        toggle(value: string) {
            let v: boolean = false;
            if (value === 'true') {
                v = true
            }
            this.$emit('input', !v);
        }
    }
    
    export default Checkbox;
</script>