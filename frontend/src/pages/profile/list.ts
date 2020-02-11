import SearchProfiles from './Search.vue';
// import SortBy from '@/components/SortBy.vue';

// FIXME: look into better ways to pass data from Django -> Vue. may also need to check full member status
function extract_membership_status() {
    const is_authenticated_tag = document.getElementById('sidebar');
    const is_authenticated_value = is_authenticated_tag.getAttribute('data-is-authenticated');
    return is_authenticated_value === 'True';
}
const is_authenticated = extract_membership_status();

new SearchProfiles({ propsData: { is_authenticated }}).$mount('#sidebar');
/*
new SortBy({
    propsData: {
        sortOptions: [
            {label: 'Relevance', value: ''},
            {label: 'Date joined', value: 'date_joined'},
            {label: 'Family name', value: 'last_name'},
        ],
    },
}).$mount('#sortby');
*/
