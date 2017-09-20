import {Component, Prop} from 'vue-property-decorator'
import * as Vue from 'vue'
import Vuex from 'vuex'
import VueRouter from 'vue-router'

import Contributors from './contributors'
import Upload from './upload'
import CodebaseReleaseMetadata from './detail'
import {store} from './store'

Vue.use(Vuex);
Vue.use(VueRouter);

const component = {
    template: '<div>TODO</div>'
};

@Component(<any>{
    store: new Vuex.Store(store),
    template: `<div>
        <div v-if="isInitialized">
            <h1>{{ $store.state.release.codebase.title }} <i>v{{ $store.state.release.version_number }}</i> <span class="badge badge-secondary" v-if="isPublished">Published</span></h1>
            <ul class="nav">
                <li class="nav-item" v-if="!isPublished">
                    <router-link :to="{ name: 'code_upload'}" class="nav-link" active-class="disabled">Upload Code</router-link>
                </li>
                <li class="nav-item" v-if="!isPublished">
                    <router-link :to="{ name: 'data_upload'}" class="nav-link" active-class="disabled">Upload Data</router-link>
                </li>
                <li class="nav-item" v-if="!isPublished">
                    <router-link :to="{ name: 'documentation_upload'}" class="nav-link" active-class="disabled">Upload Documentation</router-link>
                </li>
                <li class="nav-item" v-if="!isPublished">
                    <router-link :to="{ name: 'image_upload'}" class="nav-link" active-class="disabled">Upload Images</router-link>
                </li>
                <li class="nav-item">
                    <router-link :to="{ name: 'contributors' }" class="nav-link" active-class="disabled">Contributors</router-link>
                </li>
                <li class="nav-item">
                    <router-link :to="{ name: 'detail' }" class="nav-link" active-class="disabled">
                        Detail<span class="badge badge-pill badge-danger" v-if="detailPageErrors !== 0">{{ detailPageErrors }} errors</span>
                    </router-link>
                </li>
            </ul>
            <router-view :initialData="initialData"></router-view>
        </div>
        <div v-else>
            <h1>Loading codebase release metadata...</h1>
        </div>
    </div>`,
    router: new VueRouter({
        routes: [
            {path: '/', redirect: {name: 'code_upload'}},
            {
                path: '/code_upload/', component: Upload, name: 'code_upload',
                props: {
                    uploadType: 'sources',
                    acceptedFileTypes: 'text/plain',
                    instructions: 'Upload code associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first. Files with the same name will result in overwrites.'
                }
            },
            {
                path: '/data_upload/', component: Upload, name: 'data_upload',
                props: {
                    uploadType: 'data',
                    instructions: 'Upload data associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first. Files with the same name will result in overwrites.'
                }
            },
            {
                path: '/documentation_upload/', component: Upload, name: 'documentation_upload',
                props: {
                    uploadType: 'documentation',
                    instructions: 'Upload documentation associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first. Files with the same name will result in overwrites.'
                }
            },
            {
                path: '/image_upload/', component: Upload, name: 'image_upload',
                props: {
                    uploadType: 'images',
                    instructions: 'Upload images associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first. Files with the same name will result in overwrites.'
                }
            },
            {path: '/contributors/', component: Contributors, name: 'contributors'},
            {path: '/detail/', component: CodebaseReleaseMetadata, name: 'detail'},
        ]
    })
})
class Workflow extends Vue {
    @Prop()
    identifier: string;

    @Prop()
    version_number: string;

    isInitialized: boolean = false;

    get isPublished() {
        return this.$store.state.release.live;
    }

    get initialData() {
        switch (this.$route.name) {
            case 'contributors':
                return this.$store.getters.release_contributors;
            case 'detail':
                return this.$store.getters.detail;
            default:
                return {}
        }
    }

    get detailPageErrors() {
        return 0;
    }

    created() {
        if (this.identifier && this.version_number) {
            this.$store.dispatch('initialize', {
                identifier: this.identifier,
                version_number: this.version_number
            }).then(response => this.isInitialized = true);
        } else {
            this.isInitialized = true;
        }
    }
}

export default Workflow;