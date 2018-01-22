import {SearchCodebases} from 'pages/codebase/search';
import {SortBy} from 'components/sort-by';
import * as queryString from 'query-string';

const _queryParams = queryString.parse(window.location.search);
new SearchCodebases().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Publish date', value: 'first_published_at'},
            {label: 'Title', value: 'title'},
            {label: 'Author: family name', value: 'submitter__last_name'},
            {label: 'Author: username', value: 'submitter__username'},
            {label: 'Peer reviewed', value: 'peer_reviewed'},
        ],
    },
}).$mount('#sortby');
