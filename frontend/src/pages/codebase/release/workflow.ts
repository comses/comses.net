import {Component, Prop, Watch} from 'vue-property-decorator'
import Vue from 'vue'
import Vuex from 'vuex'
import VueRouter from 'vue-router'

import Contributors from './contributors'
import {Upload} from "components/upload";
import {UploadPage} from './upload'
import CodebaseReleaseMetadata from './detail'
import CodebaseEditForm from '../edit'
import {store} from './store'
import {CreateOrUpdateHandler} from "api/handler";
import {CodebaseReleaseAPI, CodebaseAPI} from "api";
import * as _ from 'lodash';
import yup from'yup';
import {Progress} from "pages/codebase/release/progress";
import {createFormValidator} from "pages/form";
import {HandlerWithRedirect} from "handler";
import Input from "components/forms/input";
import MessageDisplay from "components/message_display";

const codebaseReleaseAPI = new CodebaseReleaseAPI();
const codebaseAPI = new CodebaseAPI();

Vue.use(Vuex);
Vue.use(VueRouter);

type CodebaseTabs = 'metadata' | 'media';

@Component({
    template: `<div class="modal fade" id="editCodebaseModal">
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Edit Codebase</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <ul class="nav nav-tabs">
                            <li class="nav-item">
                                <a :class="['nav-link', tabClass('metadata')]" @click="setActive('metadata')">Metadata</a>
                            </li>
                            <li class="nav-item">
                                <a :class="['nav-link', tabClass('media')]" @click="setActive('media')">Media</a>
                            </li>
                        </ul>
                        <div class="tab-content">
                            <div :class="['tab-pane fade', contentClass('metadata')]">
                                <codebase-edit-form :_identifier="identifier" redirect="#editCodebaseModal" 
                                    @updated="$emit('updated', $event)">
                                </codebase-edit-form>
                            </div>
                            <div :class="['tab-pane fade', contentClass('media')]">
                                <c-upload :uploadUrl="uploadUrl" title="Upload Media" 
                                    instructions="Upload featured media files here. Images are displayed on the release detail page of every release"
                                    originalInstructions="Current media files" :originals="files" @doneUpload="getMediaFiles" 
                                    @deleteFile="deleteFile" @clear="clear">
                                </c-upload>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`,
    components: {
        'codebase-edit-form': CodebaseEditForm,
        'c-upload': Upload
    }
})
class CodebaseEditFormPopup extends Vue {
    @Prop()
    identifier: string;

    @Prop()
    redirect: boolean;

    @Prop()
    files: Array<{ name: string, identifier: any }>;

    get uploadUrl() {
        return codebaseAPI.mediaListUrl(this.identifier);
    }

    active: CodebaseTabs = 'metadata';

    isActive(name: CodebaseTabs) {
        return name == this.active;
    }

    setActive(name: CodebaseTabs) {
        this.active = name;
    }

    tabClass(name: CodebaseTabs) {
        if (name === this.active) {
            return 'active';
        } else {
            return '';
        }
    }

    contentClass(name: CodebaseTabs) {
        if (name === this.active) {
            return 'show active';
        } else {
            return ''
        }
    }

    getMediaFiles() {
        this.$store.dispatch('getMediaFiles');
    }

    async deleteFile(image_id) {
        await codebaseAPI.mediaDelete(this.identifier, image_id);
        this.getMediaFiles();
    }

    async clear() {
        await codebaseAPI.mediaClear(this.identifier);
        this.getMediaFiles();
    }
}

export const publishSchema = yup.object().shape({
   version_number: yup.string().required().matches(/\d+\.\d+\.\d+/, 'Not a valid semantic version string. Must be in MAJOR.MINOR.PATCH format.')
});

@Component({
    template: `<div class="modal fade" id="publishCodebaseReleaseModal">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Publish Codebase Release {{ _version_number }}</h5>

                    <button type="button" class="close" @click="close" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <p>Before publishing a release you must pick a semantic version to associate it with. In semantic 
                    versioning a version is composed of major, minor and patch parts. A new major version should be 
                    set if your new release is backwards incompatible with the previous release. A new release should 
                    bump the minor number is the release introduced new features but remains backwards compatible. A
                    new release should bump the patch number if the new release has bug fix release changes only.</p>
                    <c-input v-model="version_number" name="version_number" :errorMsgs="errors.version_number"
                        label="Version Number">
                        <div class="form-text text-muted" slot="help">
                            Change the semantic version before release. Please see here for more information on 
                            <a href="https://semver.org/">semantic versioning</a>
                        </div>
                    </c-input>
                    <p>
                        Publishing a codebase result release makes possible for anyone to view and download it. 
                        Published releases must have code and documentation files and at least one contributor. Once a
                        release is published files associated with the release cannot be added, modified or deleted.
                    </p>
                    <p>
                        Publishing a release cannot be undone. Do you want to continue?
                    </p>
                </div>
                <c-message-display :messages="statusMessages" @clear="clear">
                </c-message-display>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" @click="publish">Publish</button>
                    <button type="button" class="btn btn-secondary" @click="close">Cancel</button>
                </div>
            </div>
        </div>
    </div>`,
    components: {
        'c-input': Input,
        'c-message-display': MessageDisplay
    }
})
class PublishModal extends createFormValidator(publishSchema) {
    @Prop()
    identifier: string;

    @Prop()
    _version_number: number;

    @Prop()
    absolute_url: string;

    @Watch('_version_number', {immediate: true})
    setVersionNumber() {
        (<any>this).version_number = _.clone(this._version_number);
    }

    clear() {
        this.statusMessages = [];
    }

    close() {
        (<any>$('#publishCodebaseReleaseModal')).modal('hide');
        this.clear();
    }

    detailPageUrl(version_number) {
        return codebaseReleaseAPI.detailUrl({identifier: this.identifier, version_number});
    }

    publish() {
        this.clear();
        return codebaseReleaseAPI.publish({identifier: this.identifier, version_number: this._version_number},
            new HandlerWithRedirect(this));
    }
}

@Component(<any>{
    store: new Vuex.Store(store),
    components: {
        'c-publish-modal': PublishModal,
        'c-codebase-edit-form-popup': CodebaseEditFormPopup,
        'c-progress': Progress
    },
    template: `<div>
        <div v-if="isInitialized">
            <h1>{{ $store.state.release.codebase.title }} <i>v{{ $store.state.release.version_number }}</i>
                <span class="badge badge-secondary" v-if="isPublished">Published</span>
                <span v-else>
                    <span class="badge badge-warning">Unpublished</span> <span class="btn btn-sm btn-secondary" data-target="#publishCodebaseReleaseModal" data-toggle="modal">Publish</span>
                </span>
                <span class="has-pointer-cursor btn btn-sm btn-secondary" data-target="#editCodebaseModal" data-toggle="modal">Edit Common Metadata</span>
            </h1>
            <c-progress></c-progress>
            <ul class="nav nav-tabs justify-content-center">
                <li class="nav-item" v-if="!isPublished" data-toggle="tooltip" data-placement="bottom" title="">
                    <router-link :to="{ name: 'upload'}" class="nav-link required" active-class="disabled">Upload</router-link>
                </li>
                <li class="nav-item">
                    <router-link :to="{ name: 'contributors' }" class="nav-link required" active-class="disabled">Contributors</router-link>
                </li>
                <li class="nav-item">
                    <router-link :to="{ name: 'detail' }" class="nav-link required" active-class="disabled">
                        Detail<span class="badge badge-pill badge-danger" v-if="detailPageErrors !== 0">{{ detailPageErrors }} errors</span>
                    </router-link>
                </li>
            </ul>
            <keep-alive>
                <router-view :initialData="initialData"></router-view>
            </keep-alive>
            <c-codebase-edit-form-popup :identifier="identifier" :redirect="false" :files="$store.state.files.media" @updated="setCodebase"></c-codebase-edit-form-popup>
            <c-publish-modal :_version_number="version_number" :identifier="identifier" :absolute_url="absolute_url"></c-publish-modal>
        </div>
        <div v-else>
            <h1>Loading codebase release metadata...</h1>
        </div>
    </div>`,
    router: new VueRouter({
        routes: [
            {path: '/', redirect: {name: 'contributors'}},
            {path: '/upload', component: UploadPage, name: 'upload'},
            {path: '/contributors/', component: Contributors, name: 'contributors'},
            {path: '/detail/', component: CodebaseReleaseMetadata, name: 'detail'}
        ]
    })
})
class Workflow extends Vue {
    @Prop()
    identifier: string;

    @Prop()
    version_number: string;

    isInitialized: boolean = false;

    get absolute_url() {
        return this.$store.state.release.absolute_url;
    }

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

    setCodebase(codebase) {
        this.$store.commit('setCodebase', codebase);
    }
}

export default Workflow;
