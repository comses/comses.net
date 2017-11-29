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
            <div :class="fileUploadAlertClass(info)" v-for="(info, name) in fileUploadMsgs">
                <span v-if="info.kind === 'success'">
                    File {{ name }} uploaded sucessfully!
                </span>
                <span v-else-if="info.kind === 'progress'">
                    File upload {{ name }} is <b>{{ info.percentCompleted }}%</b> complete
                </span>
                <span v-else-if="info.kind == 'failure'">
                    <div v-for="msg in info.msgs">
                        <b>{{ msg.msg.stage }}</b>: {{ msg.msg.detail }}
                    </div>
                </span>
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

    fileUploadMsgs: { [name: string]: UploadInfo } = {};

    fileUploadAlertClass(uploadInfo: UploadInfo) {
        switch (uploadInfo.kind) {
            case 'success':
                return 'alert alert-success';
            case 'progress':
                return 'alert alert-secondary';
            case 'failure':
                return 'alert alert-danger';
        }
    }

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
            this.$set(this.fileUploadMsgs, file.name, {kind: 'progress', percentCompleted, size: file.size});
        };
        try {
            await codebaseReleaseAPI.uploadFile(
                {identifier: this.identifier, version_number: this.version_number, category: this.uploadType},
                file, onUploadProgress);
        } catch(error) {
            if (error.response) {
                this.$set(this.fileUploadMsgs, file.name, {kind: 'failure', msgs: error.response.data})
            }
        }
        _.delay(() => this.$delete(this.fileUploadMsgs, file.name), 3000);
        await Promise.all([
            this.$store.dispatch('getOriginalFiles', this.uploadType),
            this.$store.dispatch('getSipFiles', this.uploadType)
        ]);
        event.target.value = null;
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