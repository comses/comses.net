import {SearchCodebases} from 'pages/codebase/search';
import {SortBy} from 'components/sort-by';
import * as queryString from 'query-string';

const _queryParams = queryString.parse(window.location.search);
new SearchCodebases().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Publish date', value: 'first_published_at'},
            {label: 'Last modified', value: 'last_modified'},
            {label: 'Peer reviewed', value: 'peer_reviewed'},
            {label: 'Title', value: 'title'},
            {label: 'Author', value: 'author'},
        ],
    },
}).$mount('#sortby');
