import Workflow from './workflow'

function extractParams(pathname: string) {
    const el = document.getElementById('app');
    const version_number = el.getAttribute('data-version-number');
    const identifier = el.getAttribute('data-identifier');
    const review_status_enum = JSON.parse(el.getAttribute('data-review-status-enum'));
    return {identifier, version_number, review_status_enum}
}

new Workflow({propsData: extractParams(window.location.pathname)}).$mount('#app');