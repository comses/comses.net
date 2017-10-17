import {Component, Prop} from 'vue-property-decorator'
import * as Vue from 'vue'
import Vuex from 'vuex'
import VueRouter from 'vue-router'

import Contributors from './contributors'
import Upload from './upload'
import CodebaseReleaseMetadata from './detail'
import {store} from './store'
import {CreateOrUpdateHandler} from "api/handler";
import {codebaseReleaseAPI} from "api";
import $ from 'jquery';
import * as _ from 'lodash';

Vue.use(Vuex);
Vue.use(VueRouter);

@Component({
    name: 'c-publish-modal',
    template: `<div class="modal fade" id="publishCodebaseReleaseModal">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Publish Codebase Release {{ version_number }}</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <p>
                        Publishing a codebase result release makes possible for anyone to view and download it. 
                        Published releases must have code and documentation files and at least one contributor. Once a
                        release is published files associated with release cannot be added, modified or deleted.
                    </p>
                    <p>
                        Publishing a release cannot be undone. Do you want to continue?
                    </p>
                </div>
                <div class=""></div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" @click="publish">Publish</button>
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                </div>
            </div>
        </div>
    </div>`
})
class PublishModal extends Vue implements CreateOrUpdateHandler {
    @Prop()
    identifier: string;

    @Prop()
    version_number: number;

    errorMessages: Array<string> = [];

    clear() {
        this.errorMessages = [];
    }

    handleOtherError(response_or_network_error) {
        this.errorMessages = ['Network error'];
    }

    handleServerValidationError(responseError) {
        const response = responseError.response;
        _.forEach(_.toPairs(response.data), (k, v) => this.errorMessages.push(`${k}: ${v}`));
    }

    handleSuccessWithoutDataResponse(response) {
        this.clear();
        $('#publishCodebaseReleaseModal').hide();
    }

    handleSuccessWithDataResponse(response) {
        this.clear();
        $('#publishCodebaseReleaseModal').hide();
    }

    publish() {
        this.clear();
        return codebaseReleaseAPI.publish({identifier: this.identifier, version_number: this.version_number}, this);
    }
}

@Component(<any>{
    store: new Vuex.Store(store),
    components: {
        PublishModal
    },
    template: `<div>
        <div v-if="isInitialized">
            <h1>{{ $store.state.release.codebase.title }} <i>v{{ $store.state.release.version_number }}</i> 
                <span class="badge badge-secondary" v-if="isPublished">Published</span>
                <span class="badge badge-danger" data-target="publishCodebaseReleaseModal" v-else>Unpublished</span>
            </h1>
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
            <c-publish-modal :version_number="version_number" :identifier="identifier"></c-publish-modal>
        </div>
        <div v-else>
            <h1>Loading codebase release metadata...</h1>
        </div>
    </div>`,
    router: new VueRouter({
        routes: [
            {path: '/', redirect: {name: 'contributors'}},
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