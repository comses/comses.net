<template>
    <div :class="['form-group', hasDanger]">
        <slot name="label"></slot>
        <datepicker v-model="date" wrapper-class="input-group" :input-class="['form-control', formControlDanger]" :clear-button="clearButton"></datepicker>
        <div v-if="hasErrors" class="form-control-feedback">{{ errorMessage }}</div>
        <slot name="help"></slot>
    </div>
</template>
<script lang="ts">
    import {Component, Prop} from 'vue-property-decorator'
    import BaseControl from './base'
    import * as Datepicker from 'vuejs-datepicker'

    @Component({
        components: {
            'datepicker': Datepicker
        }
    })
    export default class InputDatepicker extends BaseControl {
        @Prop({default: false})
        clearButton: boolean;

        get date() {
            return this.value.value;
        }

        set date(value: Date) {
            this.$emit('input', {
                value: value,
                errors: this.value.errors
            });
        }
    }
</script>