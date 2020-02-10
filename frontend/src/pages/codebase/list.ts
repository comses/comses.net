import SearchCodebases from '@/pages/codebase/Search.vue';
import SortBy from '@/components/SortBy.vue';
import * as queryString from 'query-string';

const _queryParams = queryString.parse(window.location.search);
new SearchCodebases().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Relevance', value: ''},
            {label: 'Date Published', value: 'first_published_at'},
            {label: 'Last Modified', value: 'last_modified'},
            {label: 'Peer Reviewed', value: 'peer_reviewed'},
        ],
    },
}).$mount('#sortby');
