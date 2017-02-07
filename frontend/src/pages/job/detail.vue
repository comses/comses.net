<template>
    <div>
        <h1>{{ detail.title }} ({{ detail.date_created }})</h1>
        <div v-html="markdown"></div>
        <c-tag-list :tags="detail.tags"></c-tag-list>
    </div>
</template>
<style>
    body{
        background-color:#ffffff;
    }


</style>
<script lang="ts">
    import {mapGetters} from 'vuex'
    import TagList from 'components/taglist'
    import * as marked from 'marked'

    export default {
        watch: {
            '$route': function (val) {
                console.log(this.$router.resolve('/jobs/detail/1'));
                console.log(val);
            }
        },
        computed: {
            ...mapGetters('jobs', ['detail', 'list']),
            markdown() {
                return marked(this.detail.description, {sanitize: true})
            }
        },
        components: {
            'c-tag-list': TagList
        }
    }
</script>
