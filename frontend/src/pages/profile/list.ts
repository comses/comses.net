import {SearchProfiles} from './search';
import {SortBy} from "components/sort-by";

// FIXME: look into better ways to pass data from Django -> Vue. may also need to check full member status
function extract_membership_status() {
    const is_authenticated_tag = document.getElementById('sidebar');
    const is_authenticated_value = is_authenticated_tag.getAttribute('data-is-authenticated');
    return is_authenticated_value === 'True';
}
const is_authenticated = extract_membership_status();

new SearchProfiles({ propsData:{ is_authenticated }}).$mount('#sidebar');
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Relevance', value: ''},
            {label: 'Date joined', value: 'user__date_joined'},
            {label: 'Family name', value: 'user__last_name'},
        ],
    },
}).$mount('#sortby');
