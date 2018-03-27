import {SearchJobs} from './search';
import {SortBy} from "components/sort-by";

new SearchJobs().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Relevance', value: ''},
            {label: 'Publish date', value: 'date_created'},
            {label: 'Last modified date', value: 'last_modified'},
            {label: 'Application deadline', value: 'application_deadline'}
        ],
    },
}).$mount('#sortby');