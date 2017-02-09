<template>
    <div :class="['form-group', hasDanger]">
        <label class="form-control-label">{{ label }}</label>
        <input :type="type" :class="['form-control', formControlDanger]"
               v-on:change="updateValue($event.target.value)"
               v-bind:value="value">
        <div v-if="errors.length > 0" class="form-control-feedback">{{ errorMessage }}</div>
        <small class="text-muted">{{ help }}</small>
    </div>
</template>
<style>
    body{
        background-color:#ff0000;
    }

</style>
<script lang="ts">
    import { Component, Prop } from 'vue-property-decorator'
    import BaseControl from './base'

    @Component
    export default class InputChange extends BaseControl {
        @Prop
        type: string;

        @Prop
        label: string;
    }
</script>