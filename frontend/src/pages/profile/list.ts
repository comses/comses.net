import {SearchProfiles} from './search';
import {SortBy} from "components/sort-by";

function extract_membership_status() {
    const is_a_member_tag = document.getElementById('sidebar');
    const is_a_member_value = is_a_member_tag.getAttribute('data-is-a-member');
    return is_a_member_value === 'true';
}
const is_a_member = extract_membership_status();

new SearchProfiles({ propsData:{ is_a_member }}).$mount('#sidebar');
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