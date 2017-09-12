import EditCodebase from './edit'

function extractUrlParams(pathname: string) {
    let match = pathname.match(/\/codebases\/([\w-]+)\/edit\//);
    if (match !== null) {
        return { identifier: match[1] };
    }
    return { identifier: null }
}

const editCodebase = new EditCodebase({ propsData: extractUrlParams(window.location.pathname)}).$mount('#app');
console.log({editCodebase});