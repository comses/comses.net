<template>
    <div class="row">
        <div class="col-lg-10 col-sm-8"><router-link :to="{ name: 'job_detail', params: { jobId: id } }">{{title}}</router-link></div>
        <div class="col-lg-2 col-sm-4">{{ date_created }}</div>
    </div>
</template>
<style>

</style>
<script lang="ts">
    import * as Vue from 'vue'
    export default {
        props: ['id', 'title', 'date_created', 'content' ],
        components: {

        }
    } as Vue.ComponentOptions<Vue>
</script>
