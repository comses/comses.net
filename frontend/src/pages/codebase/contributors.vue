<template>
    <div>
        <c-input type="text" v-model="data.family_name" :errors="errors.family_name"></c-input>
        <c-input type="text" v-model="data.given_name" :errors="errors.given_name"></c-input>
        <c-input type="text" v-model="data.middle_name" :errors="errors.middle_name"></c-input>
        <c-input type="email" v-model="data.email" :errors="errors.email"></c-input>
    </div>
</template>
<script lang="ts">
    import * as Vue from 'vue'
    import { Component } from 'vue-property-decorator'

    import Input from 'components/forms/input.vue'

    @Component({
        'c-input': Input
    })
    export default class Contributors extends Vue {
        data;
        errors;
    }
</script>
