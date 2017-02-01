<template>
    <div class="list-group-item list-group-item-action flex-column align-items-start compact">
        <div class="d-flex w-100 justify-content-between">
            <router-link :to="{ name: 'job_detail', params: { jobId: id } }">
                {{ title }}
            </router-link>
            <small class="p-2">{{ date_created }}</small>
        </div>
    </div>
</template>
<style>

</style>
<script lang="ts">
    import * as Vue from 'vue'
    export default {
        props: ['id', 'title', 'date_created', 'description', 'to'],
        components: {}
    } as Vue.ComponentOptions<Vue>
</script>
