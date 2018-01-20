import Workflow from './workflow'

function extractParams(pathname: string) {
    const el = document.getElementById('app');
    const version_number = el.getAttribute('data-version-number');
    const identifier = el.getAttribute('data-identifier');
    return { identifier, version_number}
}

new Workflow({ propsData: extractParams(window.location.pathname)}).$mount('#app');