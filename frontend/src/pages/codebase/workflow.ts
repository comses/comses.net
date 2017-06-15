import { Component, Prop } from 'vue-property-decorator'
import * as Vue from 'vue'
import VueRouter from 'vue-router'
// import Permissions from './permissions.vue'
import Upload from './upload.vue'

Vue.use(VueRouter);

const component = {
    template: '<div>TODO</div>'
}

const template = `<div>
        <h1>Release Submission for Model ""</h1>
        <ul class="nav">
            <li class="nav-item">
                <router-link :to="{ name: 'code_upload'}" class="nav-link">Upload Code</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'data_upload'}" class="nav-link">Upload Data</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'documentation_upload'}" class="nav-link">Upload Documentation</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'contributors' }" class="nav-link">Contributors</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'description' }" class="nav-link">Description</router-link>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'permissions' }" class="nav-link">Permissions</router-link>
            </li>
        </ul>
        <router-view></router-view>
    </div>`;

const routes = [
    { path: '/code_upload/', component: Upload, name: 'code_upload',  props: { uploadUrl: 'upload_src/', acceptedFileTypes: 'text/plain'}},
    { path: '/data_upload/', component: Upload, name: 'data_upload', props: { uploadUrl: 'upload_data/'}},
    { path: '/documentation_upload/', component: Upload, name: 'documentation_upload', props: { uploadUrl: 'upload_doc/'}},
    { path: '/contributors/', component, name: 'contributors'},
    { path: '/description/', component, name: 'description'},
    { path: '/permissions/', component, name: 'permissions'},
]

const router = new VueRouter({
    routes
});

export default new Vue({
    router,
    template
});