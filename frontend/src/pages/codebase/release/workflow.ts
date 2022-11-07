import {Component, Prop, Watch} from 'vue-property-decorator';
import Vue from 'vue';
import Vuex from 'vuex';
import VueRouter from 'vue-router';

import Contributors from './contributors';
import {Upload} from '@/components/upload';
import {UploadPage} from './upload';
import CodebaseReleaseMetadata from './detail';
import CodebaseEditForm from '@/components/codebase/Edit.vue';
import {store} from './store';
import jQuery from 'jquery';
import {CreateOrUpdateHandler} from '@/api/handler';
import {CodebaseReleaseAPI, CodebaseAPI, ReviewEditorAPI} from '@/api';
import * as _ from 'lodash';
import * as yup from 'yup';
import {Progress} from '@/pages/codebase/release/progress';
import {createFormValidator} from '@/pages/form';
import {HandlerWithRedirect} from '@/api/handler';
import Input from '@/components/forms/input';
import MessageDisplay from '@/components/messages';
import {ConfirmationModal} from '@/components/confirmation';

const codebaseReleaseAPI = new CodebaseReleaseAPI();
const codebaseAPI = new CodebaseAPI();
const reviewAPI = new ReviewEditorAPI();

Vue.use(Vuex);
Vue.use(VueRouter);

type CodebaseTabs = 'metadata' | 'media';

@Component({
    template: `<div class="modal fade" id="editCodebaseModal" role='dialog'>
            <div class="modal-dialog modal-lg" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Edit Codebase</h5>
                        <button type="button" id="closeEditCodebaseModal" class="close" data-dismiss="modal" aria-label="Close">
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
                                <codebase-edit-form ref="codebaseEditForm" :_identifier="identifier" redirect="#editCodebaseModal"
                                    @updated="$emit('updated', $event)">
                                </codebase-edit-form>
                            </div>
                            <div :class="['tab-pane fade', contentClass('media')]">
                                <c-upload :uploadUrl="uploadUrl" title="Upload Media"
                                    instructions="Upload featured media files here. Images are displayed on the release detail page of every release. GIF, JPEG and PNG files only."
                                    originalInstructions="Current media files" :originals="files" @doneUpload="getMediaFiles"
                                    acceptedFileTypes="image/gif, image/jpeg, image/png"
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
        'c-upload': Upload,
    },
})
class CodebaseEditFormPopup extends Vue {
    @Prop()
    public identifier: string;

    @Prop()
    public redirect: boolean;

    @Prop()
    public files: Array<{ name: string, identifier: any }>;

    get uploadUrl() {
        return codebaseAPI.mediaListUrl(this.identifier);
    }

    public active: CodebaseTabs = 'metadata';

    public isActive(name: CodebaseTabs) {
        return name == this.active;
    }

    public setActive(name: CodebaseTabs) {
        this.active = name;
    }

    public tabClass(name: CodebaseTabs) {
        if (name === this.active) {
            return 'active';
        } else {
            return '';
        }
    }

    public contentClass(name: CodebaseTabs) {
        if (name === this.active) {
            return 'show active';
        } else {
            return '';
        }
    }

    public getMediaFiles() {
        this.$store.dispatch('getMediaFiles');
    }

    public async deleteFile(image_id) {
        await codebaseAPI.mediaDelete(this.identifier, image_id);
        this.getMediaFiles();
    }

    public async clear() {
        await codebaseAPI.mediaClear(this.identifier);
        this.getMediaFiles();
    }

    public mounted() {
      this.$nextTick(() => {
        const self = this;
        jQuery('#editCodebaseModal').on('show.bs.modal', function(e) {
          setTimeout(() => {
            (self.$refs.codebaseEditForm as any).refresh();
          }, 500);
        });
      });
    }
}

export const publishSchema = yup.object().shape({
   version_number: yup.string().required().matches(/\d+\.\d+\.\d+/, 'Not a valid semantic version string. Must be in MAJOR.MINOR.PATCH format.'),
});

@Component({
    template: `<div class="modal fade" id="publishCodebaseReleaseModal">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h4 class="modal-title">Publish Codebase Release {{ _version_number }}</h4>
                    <button type="button" data-dismiss='modal' class="close" @click="close" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <p><b>Please read carefully!</b> <b>Publishing</b> a release makes it possible for anyone to view and download it. Once a
                    release is published, the files associated with the release will be <b>frozen</b> and you will no
                    longer be able to add or remove files to the release. You will still be able to edit your model's
                    metadata. If you'd like to request <a href='/reviews/'>a peer review</a> of your model you
                    should do that first so you may address any concerns raised during the peer review process that may
                    include changes to the files associated with your release.
                    </p>
                    <p>Please assign a semantic version number to this release. CoMSES Net currently uses the
                    <a target='_blank' href='https://semver.org'>semantic versioning</a> standard, which splits a
                    version number into three parts: major, minor and patch. For example, version 2.7.18 has major
                    version 2, minor version 7, and patch version 18. You should increase the <i>major</i> version
                    (leftmost number) if this new release is backwards incompatible with the previous release. You
                    should increase the <i>minor</i> version (middle number) if this release introduced new features but
                    remains backwards compatible. And finally, you should increase the <i>patch</i> version (rightmost
                    number) if this release only contains bug fixes and remains backwards compatible (sans the bugs of
                    course!).
                    </p>
                    <c-input v-model="version_number" name="version_number" :errorMsgs="errors.version_number"
                        label="Version Number">
                        <small class="form-text text-muted" slot="help">
                            <a target='_blank' href="https://semver.org/">more info on semantic versioning</a>
                        </small>
                    </c-input>
                    <p>
                        Publishing a release cannot be undone. Do you want to continue?
                    </p>
                </div>
                <c-message-display :messages="statusMessages" @clear="clear">
                </c-message-display>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-dismiss='modal' @click="close">Cancel</button>
                    <button class="btn btn-danger ml-auto" @click="publish"><i class='fas fa-share-alt'></i> Publish</button>
                </div>
            </div>
        </div>
    </div>`,
    components: {
        'c-input': Input,
        'c-message-display': MessageDisplay,
    },
})
class PublishModal extends createFormValidator(publishSchema) {
    @Prop()
    public identifier: string;

    @Prop()
    public _version_number: number;

    @Prop()
    public absolute_url: string;

    @Watch('_version_number', {immediate: true})
    public setVersionNumber() {
        (this as any).version_number = _.clone(this._version_number);
    }

    public clear() {
        this.statusMessages = [];
    }

    public close() {
        ($('#publishCodebaseReleaseModal') as any).modal('hide');
        this.clear();
    }

    public detailPageUrl(version_number) {
        return codebaseReleaseAPI.detailUrl({identifier: this.identifier, version_number});
    }

    public publish() {
        this.clear();
        return codebaseReleaseAPI.publish({identifier: this.identifier, version_number: this._version_number},
            new HandlerWithRedirect(this));
    }
}

@Component({
    store: new Vuex.Store(store),
    components: {
        'c-confirmation-modal': ConfirmationModal,
        'c-publish-modal': PublishModal,
        'c-codebase-edit-form-popup': CodebaseEditFormPopup,
        'c-progress': Progress,
    },
    template: `<div>
        <div v-if="isInitialized">
            <h1>
            <span v-if='! isPublished' title='This release is currently private and unpublished.' class="disabled btn btn-warning"><i class='fas fa-lock'></i> Private</span>
            {{ $store.state.release.codebase.title }} <i>v{{ $store.state.release.version_number }}</i>
            </h1>
            <h5 class="text-muted">
            Peer Review Status: {{ reviewStatus }} | <a :href='absolute_url'>View Live</a>
            <a class='float-right' href='//forum.comses.net/t/archiving-your-model-1-getting-started/7377'><i class='fas fa-question-circle'></i> Need help? Check out our archiving tutorial</a>
            </h5>
            <div class='pb-2'>
                <span class="btn btn-primary" data-target="#editCodebaseModal" data-toggle="modal"><i class='fas fa-edit'></i> Edit Common Metadata | Add Images &amp; Media</span>
                <div class='float-right'>
                    <span class="btn btn-outline-danger" v-if="!hasReview" data-target="#peerReviewModal" data-toggle="modal">Request Peer Review</span>
                    <span class="btn btn-outline-danger" v-else-if="isAwaitingAuthorChanges" data-target="#notifyReviewersModal" data-toggle="modal">Notify Reviewers of Changes</span>
                    <span class="disabled btn btn-info" v-if="isPublished"><i class='fas fa-share-alt'></i> Published</span>
                    <span v-else>
                        <span class="btn btn-danger" data-target="#publishCodebaseReleaseModal" data-toggle="modal"><span class='fas fa-share-alt'></span> Publish</span>
                    </span>
                </div>
            </div>
            <c-progress></c-progress>
            <ul class="nav nav-tabs justify-content-center">
                <li class="nav-item">
                    <router-link :to="{ name: 'detail' }" class="nav-link" active-class="active">
                        Metadata<span class="badge badge-pill badge-danger" v-if="detailPageErrors !== 0">{{ detailPageErrors }} errors</span>
                    </router-link>
                </li>
                <li class="nav-item">
                    <router-link :to="{ name: 'contributors' }" class="nav-link" active-class="active">Contributors</router-link>
                </li>
                 <li class="nav-item" v-if="!isPublished" data-toggle="tooltip" data-placement="bottom" title="">
                    <router-link :to="{ name: 'upload'}" class="nav-link" active-class="active">Upload</router-link>
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
        <c-confirmation-modal title="Request Peer Review" base_name="peerReviewModal" :url="requestPeerReviewUrl"
            @success="handlePeerReviewCreation">
            <template slot="body">
                <p>Are you sure you want to request a peer review of your release?</p>
            </template>
        </c-confirmation-modal>
        <c-confirmation-modal title="Notify Reviewers of Changes" base_name="notifyReviewersModal"
            :url="notifyReviewersOfChangesUrl" @success="setReviewStatus">
            <template slot="body">
                <p>Do you want to notify any reviewers of changes?</p>
            </template>
        </c-confirmation-modal>
    </div>`,
    router: new VueRouter({
        routes: [
            {path: '/', redirect: {name: 'detail'}},
            {path: '/detail/', component: CodebaseReleaseMetadata, name: 'detail'},
            {path: '/upload', component: UploadPage, name: 'upload'},
            {path: '/contributors/', component: Contributors, name: 'contributors'},
        ],
    }),
} as any)
class Workflow extends Vue {
    @Prop()
    public identifier: string;

    @Prop()
    public version_number: string;

    @Prop()
    public review_status_enum: object;

    public isInitialized: boolean = false;

    get requestPeerReviewUrl() {
        return this.$store.state.release.urls.request_peer_review;
    }

    get notifyReviewersOfChangesUrl() {
        return this.$store.state.release.urls.notify_reviewers_of_changes;
    }

    get isAwaitingAuthorChanges() {
        return this.$store.state.release.review_status === 'awaiting_author_changes';
    }

    get hasReview() {
        return !_.isNull(this.$store.state.release.review_status);
    }

    get reviewStatus() {
        const status = this.$store.state.release.review_status;
        if (_.isNull(status)) {
            return 'Unreviewed';
        }
        return this.review_status_enum[this.$store.state.release.review_status];
    }

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
                return {};
        }
    }

    get detailPageErrors() {
        return 0;
    }

    public created() {
        if (this.identifier && this.version_number) {
            this.$store.dispatch('initialize', {
                identifier: this.identifier,
                version_number: this.version_number,
            }).then((response) => this.isInitialized = true);
        } else {
            this.isInitialized = true;
        }
    }

    public setCodebase(codebase) {
        this.$store.commit('setCodebase', codebase);
    }

    public setReviewStatus(review_status) {
        this.$store.commit('setReviewStatus', review_status);
    }

    public setUrls(urls) {
        this.$store.commit('setUrls', urls);
    }

    public handlePeerReviewCreation(data) {
        this.setReviewStatus(data.review_status);
        this.setUrls(data.urls);
    }
}

export default Workflow;
