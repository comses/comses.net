import {SearchEvents} from '@/pages/event/Search.vue';
import {SortBy} from '@/components/sort-by';

new SearchEvents().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Relevance', value: ''},
            {label: 'Start date', value: 'start_date'},
            {label: 'Submission deadline', value: 'submission_deadline'},
            {label: 'Early registration deadline', value: 'early_registration_deadline'},
            {label: 'Date posted', value: 'date_created'},
            {label: 'Recently modified', value: 'last_modified'},
        ],
    },
}).$mount('#sortby');
