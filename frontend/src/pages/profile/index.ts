import EditProfile from './edit'

function extractParams() {
    const el = document.getElementById('app');
    const pk = el.getAttribute('data-user-pk');
    console.debug("returning " + pk);
    return {pk}
}
new EditProfile({ propsData: extractParams()}).$mount('#app');
