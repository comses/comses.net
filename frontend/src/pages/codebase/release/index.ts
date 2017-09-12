import Workflow from './workflow'

function extractUrlParams(pathname: string) {
    let match = pathname.match(/\/codebases\/([\w\-]+)\/releases\/(\d+\.\d+\.\d+)\/edit\//);
    if (match !== null) {
        return { identifier: match[1], version_number: match[2] };
    }
    return { identifier: null, version_number: null}
}

new Workflow({ propsData: extractUrlParams(window.location.pathname)}).$mount('#app');