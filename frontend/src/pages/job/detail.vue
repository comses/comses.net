<template>
    <div>
        <h1>{{ detail.title }} ({{ detail.date_created }})</h1>
        <p>{{ detail.description }}</p>
        <span v-for="tag in detail.tags" class="p-2 m-1 badge badge-primary">{{ tag.name }}</span>
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
