import {SearchJobs} from './search';
import {SortBy} from "@/components/sort-by";

new SearchJobs().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Relevance', value: ''},
            {label: 'Application deadline', value: 'application_deadline'},
            {label: 'Date posted', value: 'date_created'},
            {label: 'Recently modified ', value: 'last_modified'},
        ],
    },
}).$mount('#sortby');
