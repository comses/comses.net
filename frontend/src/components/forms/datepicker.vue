<template>
    <div :class="['form-group', {'has-danger': hasDanger}]">
        <slot name="label"></slot>
        <datepicker :value="value" @input="updateValue" wrapper-class="input-group"
                    :input-class="{'form-control': true, 'form-control-danger': hasDanger}" :clear-button="clearButton" @cleared="cleared">
        </datepicker>
        <div v-if="hasDanger" class="form-control-feedback">{{ errorMessage }}</div>
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

        cleared() {
            this.updateValue(null);
        }
    }
</script>