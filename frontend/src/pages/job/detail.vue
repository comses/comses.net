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
    import {mapGetters} from 'vuex'

    export default {
        watch: {
            '$route': function (val) {
                console.log(this.$router.resolve('/jobs/detail/1'));
                console.log(val);
            }
        },
        computed: {
            ...mapGetters('jobs', ['detail', 'list'])
        }
    }
</script>
