import '@/pages/sentry';
import EditProfile from './Edit.vue';

function extractParams() {
    const el = document.getElementById('app');
    const _pk = el.getAttribute('data-user-pk');
    console.debug('returning ' + _pk);
    return {_pk};
}
new EditProfile({ propsData: extractParams()}).$mount('#app');
