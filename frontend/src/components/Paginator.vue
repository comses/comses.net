<template>
    <nav aria-label="Paginator">
        <ul class="pagination">
            <li v-for="p in range" :class="{ 'page-item': true, active: p == page }">
                <router-link :to="{ name: route, query: { page: p, query } }"
                             class="page-link">
                    {{ p }}
                </router-link>
            </li>
        </ul>
    </nav>
</template>
<script lang="ts">
    import {mapGetters} from 'vuex'
    import * as _ from 'lodash'

    export default {
        props: ['n_pages', 'page', 'on_click', 'route', 'query'],
        computed: {
            range() {
                const lb = _.clamp(this.page - 4, 1, this.n_pages);
                const ub = _.clamp(this.page + 5, 1, this.n_pages);
                return _.range(lb, ub);
            }
        }
    }
</script>
