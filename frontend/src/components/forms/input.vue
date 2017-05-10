<template>
    <div :class="['form-group', {'has-danger': hasDanger }]">
        <slot name="label"></slot>
        <input type="text" :name="name" class="form-control" :value="value" @input="updateValue($event.target.value)">
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
    export default class Input extends BaseControl {}
</script>