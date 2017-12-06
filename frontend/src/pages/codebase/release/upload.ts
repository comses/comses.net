import {Component, Prop} from 'vue-property-decorator'
import * as Vue from 'vue'
import Vuex from 'vuex'
import {exposeComputed} from './store'
import * as _ from 'lodash'
import {CodebaseReleaseAPI} from "api/index";

const codebaseReleaseAPI = new CodebaseReleaseAPI();

Vue.use(Vuex);

interface UploadSuccess {
    kind: 'success'
    msg: string
}

interface UploadProgress {
    kind: 'progress'
    percentCompleted: number
    size: number
}

interface UploadFailure {
    kind: 'failure'
    msgs: Array<{ level: string, msg: {detail: string, stage: string}}>
}

type UploadInfo = UploadSuccess | UploadProgress | UploadFailure;

@Component(<any>{
    template: `<div>
        <slot name="label"></slot>
        <small class="form-text text-muted" v-if="instructions">{{ instructions }}</small>
        <div class="d-flex justify-content-between">
            <div>
                <label for="upload"><div class="btn btn-primary">Upload a file</div></label>
                <input class="invisible" id="upload" type="file" @change="handleFiles($event)">
            </div>
            <div>
                <button class="btn btn-outline-warning" @click="clear">Remove all files</button>
            </div>
        </div>
        <div>
            <div class="alert alert-secondary" v-for="(info, name) in fileUploadProgressMsgs">
                File upload {{ name }} is <b>{{ info.percentCompleted }}%</b> complete
            </div>
            <div class="alert alert-danger alert-dismissable" v-if="hasErrors">
                <button class="close" aria-label="Close" @click="clearUploadErrors">
                    <span aria-hidden="true"><span class="fa fa-close"></span></span>
                </button>
                <div v-for="(error, name) in fileUploadErrorMsgs">
                    <div v-for="msg in error.msgs"><b>{{ msg.msg.stage }}</b>: {{ msg.msg.detail }}</div>
                </div>
            </div>
        </div>
        <small class="form-text text-muted">
            {{ originalInstructions }}
        </small>
        <div class="list-group" v-if="originals.length > 0">
            <div class="list-group-item d-flex justify-content-between align-items-center" v-for="file in originals">
                {{ file.path }}
                <button class="btn btn-sm btn-danger pull-right" @click="deleteFile(file.url)">
                    <span class="fa fa-remove"></span>
                </button>
            </div>
        </div>
        <p v-else>
            No files uploaded
        </p>
        <small class="form-text text-muted">
            Expanded files you uploaded. When an archive (zip, tar, rar) file is uploaded it gets expanded here.
        </small>
        <div class="list-group" v-if="sip.length > 0">
            <div class="list-group-item" v-for="path in sip">
                {{ path }}
            </div>
        </div>
        <p v-else>
            No derived files
        </p>
    </div>`
})
export default class Upload extends Vue {
    @Prop
    uploadType: string;

    fileUploadErrorMsgs: { [name: string]: UploadInfo } = {};
    fileUploadProgressMsgs: { [name: string]: UploadProgress } = {};


    @Prop({default: ''})
    instructions: string;

    @Prop({default: ''})
    acceptedFileTypes: string;

    @Prop({default: ''})
    originalInstructions: string;

    async handleFiles(event) {
        const file = event.target.files[0];
        const onUploadProgress = (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            this.$set(this.fileUploadProgressMsgs, file.name, {kind: 'progress', percentCompleted, size: file.size});
        };
        _.delay(() => this.$delete(this.fileUploadProgressMsgs, file.name), 3000);
        try {
            await codebaseReleaseAPI.uploadFile(
                {identifier: this.identifier, version_number: this.version_number, category: this.uploadType},
                file, onUploadProgress);
        } catch(error) {
            if (error.response) {
                this.$set(this.fileUploadErrorMsgs, file.name, {kind: 'failure', msgs: error.response.data})
            }
        }
        await Promise.all([
            this.$store.dispatch('getOriginalFiles', this.uploadType),
            this.$store.dispatch('getSipFiles', this.uploadType)
        ]);
        event.target.value = null;
    }

    clearUploadErrors() {
        this.fileUploadErrorMsgs = {};
    }

    get hasErrors() {
        return !_.isEmpty(this.fileUploadErrorMsgs);
    }

    get version_number() {
        return this.$store.state.release.version_number;
    }

    get identifier() {
        return this.$store.state.release.codebase.identifier;
    }

    get originals() {
        return this.$store.state.files.originals[this.uploadType];
    }

    get sip() {
        return this.$store.state.files.sip[this.uploadType];
    }

    deleteFile(path: string) {
        this.$store.dispatch('deleteFile', {category: this.uploadType, path});
    }

    clear() {
        this.$store.dispatch('clearCategory', {identifier: this.identifier, version_number: this.version_number,
            category: this.uploadType});
    }
}