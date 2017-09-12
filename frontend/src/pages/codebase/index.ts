import EditCodebase from './edit'

function extractUrlParams(pathname: string) {
    let match = pathname.match(/\/codebases\/([\w-]+)\/edit\//);
    if (match !== null) {
        return { _identifier: match[1] };
    }
    return { _identifier: null }
}

const editCodebase = new EditCodebase({ propsData: extractUrlParams(window.location.pathname)}).$mount('#app');
console.log({editCodebase});