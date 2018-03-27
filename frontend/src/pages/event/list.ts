import {SearchEvents} from 'pages/event/search';
import {SortBy} from "components/sort-by";

new SearchEvents().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Relevance', value: ''},
            {label: 'Publish date', value: 'date_created'},
            {label: 'Last modified date', value: 'last_modified'},
            {label: 'Early registration deadline', value: 'early_registration_deadline'},
            {label: 'Submission deadline', value: 'submission_deadline'},
            {label: 'Start date', value: 'start_date'},
        ],
    },
}).$mount('#sortby');