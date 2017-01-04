<template>
    <nav aria-label="Paginator">
        <ul class="pagination">
            <li v-for="p_ind in range" :class="{ 'page-item': true, active: p_ind == page_ind }">
                <router-link :to="{ name: route, query: { page_ind: p_ind, query } }"
                             class="page-link">
                    {{ p_ind }}
                </router-link>
            </li>
        </ul>
    </nav>
</template>
<style>
</style>
<script lang="ts">
    import {mapGetters} from 'vuex'
    import * as _ from 'lodash'

    export default {
        props: ['n_pages', 'page_ind', 'on_click', 'route', 'query'],
        computed: {
            range() {
                const lb = _.clamp(this.page_ind - 4, 1, this.n_pages);
                const ub = _.clamp(this.page_ind + 5, 1, this.n_pages);
                return _.range(lb, ub);
            }
        }
    }
</script>
