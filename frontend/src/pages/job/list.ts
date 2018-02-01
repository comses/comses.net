import {SearchJobs} from './search';
import {SortBy} from "components/sort-by";

new SearchJobs().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Publish date', value: 'date_created'},
            {label: 'Last modified date', value: 'last_modified'},
            {label: 'Title', value: 'title'},
            {label: 'Submitter: family name', value: 'submitter__last_name'},
            {label: 'Submitter: username', value: 'submitter__username'},
        ],
    },
}).$mount('#sortby');