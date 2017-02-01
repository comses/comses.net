<template>
    <div>
        <h1>{{ detail.title }} ({{ detail.date_created }})</h1>
        <p>{{ detail.description }}</p>
    </div>
</template>
<style>
    body{
        background-color:#ffffff;
    }
</style>
<script lang="ts">
    import { mapGetters } from 'vuex'

    export default {
        computed:  {
            ...mapGetters('jobs', ['detail', 'list'])
        }
    }
</script>
