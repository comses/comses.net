import SearchCodebases from '@/pages/codebase/Search.vue';
import SortBy from '@/components/SortBy.vue';
import * as queryString from 'query-string';

const _queryParams = queryString.parse(window.location.search);
new SearchCodebases().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Title', value: 'title'},
            {label: 'Date published', value: 'first_published_at'},
            {label: 'Author: family name', value: 'submitter__last_name'},
        ],
    },
}).$mount('#sortby');
