import EditProfile from './edit'

function matchUpdateUrl(pathname: string): string | null {
    let match = pathname.match(/\/users\/([0-9a-z\_\-]+)\/edit\//);
    if (match !== null) {
        return match[1];
    }
    return match
}

const username = matchUpdateUrl(window.location.pathname);

new EditProfile({ propsData: {username}}).$mount('#app');