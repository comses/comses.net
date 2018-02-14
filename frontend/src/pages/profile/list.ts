import {SearchProfiles} from './search';
import {SortBy} from "components/sort-by";

new SearchProfiles().$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Relevance', value: ''},
            {label: 'Date joined', value: 'user__date_joined'},
            {label: 'Family name', value: 'user__last_name'},
            {label: 'Given name', value: 'user__first_name'},
        ],
    },
}).$mount('#sortby');