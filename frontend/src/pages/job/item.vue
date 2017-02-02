<template>
    <div class="list-group-item list-group-item-action row">
        <div class="col-xs-12 col-sm-6 col-md-2">
            <router-link :to="{ name: update_page, params: { jobId: id } }" class="p-2 fa fa-edit">
            </router-link>
            <router-link :to="{ name: detail_page, params: { jobId: id } }" class="p-2 fa fa-eye">
            </router-link>
        </div>
        <div class="col-xs-12 col-md-8 flex-sm-last flex-md-unordered">
            <span>{{ title }}</span>
        </div>
        <small class="col-xs-12 col-sm-6 col-md-2 text-right">{{ date_created }}</small>
    </div>
</template>
<style>

</style>
<script lang="ts">
    import * as Vue from 'vue'
    export default {
        props: ['id', 'title', 'date_created', 'description', 'detail_page', 'update_page'],
        components: {}
    } as Vue.ComponentOptions<Vue>
</script>
