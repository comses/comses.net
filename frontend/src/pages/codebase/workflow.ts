import { Component, Prop } from 'vue-property-decorator'
import * as Vue from 'vue'
import Vuex from 'vuex'
import VueRouter from 'vue-router'
import { Validator } from 'vee-validate'
import { CodebaseReleaseEdit } from 'store/common'
import { api } from 'api/index'

import Contributors from './contributors'
import Permissions from './permissions'
import Upload from './upload.vue'
import CodebaseMetadata from './codebase_metadata'
import CodebaseReleaseMetadata from './codebase_release_metadata'
import { store, exposeComputed } from './store'

Vue.use(Vuex);
Vue.use(VueRouter);

const component = {
    template: '<div>TODO</div>'
}

@Component(<any>{
    store : new Vuex.Store(store),
    template: `<div>
        <h1>{{ $store.state.codebase.title }} <i>v{{ $store.state.version_number }}</i></h1>
        <ul class="nav">
            <li class="nav-item">
                <router-link :to="{ name: 'codebase'}" class="nav-link" active-class="disabled">Model Metadata</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'code_upload'}" class="nav-link" active-class="disabled">Upload Code</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'data_upload'}" class="nav-link" active-class="disabled">Upload Data</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'documentation_upload'}" class="nav-link" active-class="disabled">Upload Documentation</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'contributors' }" class="nav-link" active-class="disabled">Contributors</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'description' }" class="nav-link" active-class="disabled">Release Metadata</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'permissions' }" class="nav-link" active-class="disabled">Permissions</router-link>
            </li>
        </ul>
        <router-view></router-view>
        <!--<button class="btn btn-primary" type="button" @click="createOrSubmit">Submit</button>-->
    </div>`,
    router: new VueRouter({
        routes: [
            { path: '/codebase/', component: CodebaseMetadata, name: 'codebase' },
            { path: '/code_upload/', component: Upload, name: 'code_upload',  
                props: { 
                    uploadType: 'sources',
                    acceptedFileTypes: 'text/plain',
                    instructions: 'Upload code associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first. Files with the same name will result in overwrites.'
                }},
            { path: '/data_upload/', component: Upload, name: 'data_upload', 
                props: { 
                    uploadType: 'data',
                    instructions: 'Upload data associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first. Files with the same name will result in overwrites.'
                }},
            { path: '/documentation_upload/', component: Upload, name: 'documentation_upload', 
                props: { 
                    uploadType: 'documentation',
                    instructions: 'Upload documentation associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first. Files with the same name will result in overwrites.'
                }},
            { path: '/contributors/', component: Contributors, name: 'contributors'},
            { path: '/description/', component: CodebaseReleaseMetadata, name: 'description'},
            { path: '/permissions/', component: Permissions, name: 'permissions', props: { permissions: { license: 'GPL V3', live: false }}},
        ]
    })
})
class Workflow extends Vue {
    created() {
        this.$store.dispatch('initialize', {identifier: '2274', version_number: '1.0.0'});
    }

    createOrSubmit() {
        console.log('submit codebase');
    }
}

export default new Workflow();