<template>
    <div>
        <h1>{{ job_detail.title }} ({{ job_detail.date_created }})</h1>
        <p>{{ job_detail.content }}</p>
    </div>
</template>
<style>
    body{
        background-color:#ffffff;
    }
</style>
<script lang="ts">
    import { mapGetters } from 'vuex'
    import store from '../store/index'

    export default {
        computed: mapGetters(['job_detail']),

        beforeRouteEnter (to, from, next) {
            // Load job detail if not part of vuex state already
            console.log({ jobId: to.params.jobId });
            store.dispatch('retrieveOrGetJob', to.params.jobId);
            next();
        }
    }
</script>
