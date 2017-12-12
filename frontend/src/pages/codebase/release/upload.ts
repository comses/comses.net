import {Component, Prop} from 'vue-property-decorator'
import {createDecorator} from 'vue-class-component';
import * as Vue from 'vue'
import Vuex from 'vuex'
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
    msgs: Array<{ level: string, msg: { detail: string, stage: string } }>
}

type UploadInfo = UploadSuccess | UploadProgress | UploadFailure;

@Component(<any>{
    template: `<div>
        <h1 class="mt-4">{{ title }}</h1>
        <slot name="label"></slot>
        <small class="form-text text-muted" v-if="instructions">{{ instructions }}</small>
        <div class="d-flex justify-content-between">
            <div>
                <label :for="upload_id"><div class="btn btn-primary">Upload a file</div></label>
                <input class="invisible" :id="upload_id" type="file" @change="handleFiles($event)">
            </div>
            <div>
                <button class="btn btn-outline-warning" @click="clear">Remove all {{ uploadType }} files</button>
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

    @Prop()
    title: string;

    @Prop({default: ''})
    instructions: string;

    @Prop({default: ''})
    acceptedFileTypes: string;

    @Prop({default: ''})
    originalInstructions: string;

    @Prop()
    identifier: string;

    @Prop()
    version_number: string;

    @Prop()
    originals: Array<any>;

    @Prop()
    sip: Array<any>;

    get upload_id() {
        return `${this.uploadType}_id`;
    }

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
        } catch (error) {
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

    deleteFile(path: string) {
        this.$store.dispatch('deleteFile', {category: this.uploadType, path});
    }

    clear() {
        this.$store.dispatch('clearCategory', {
            identifier: this.identifier, version_number: this.version_number,
            category: this.uploadType
        });
    }
}


@Component(<any>{
    template: `<div>
            <c-upload :path="config.path" :uploadType="config.uploadType" :acceptedFileTypes="config.acceptedFileTypes"
                :instructions="config.instructions" :originalInstructions="config.originalInstructions" 
                :version_number="version_number" :identifier="identifier" :originals="originals(config.uploadType)"
                :sip="sip(config.uploadType)" :title="config.title" v-for="config in configs" :key="config.uploadType">    
            </c-upload>
        </div>`,
    components: {
        'c-upload': Upload
    }
})
export class UploadPage extends Vue {
    configs = [
        {
            path: '/code_upload/',
            uploadType: 'code',
            acceptedFileTypes: 'text/plain',
            title: 'Upload Code',
            instructions: 'Upload code associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first.',
            originalInstructions: 'The original files uploaded show here. It is possible to have one archive or many non archive files. Files should be code but all files are accepted'
        },
        {
            path: '/data_upload/',
            uploadType: 'data',
            title: 'Upload Data',
            instructions: 'Upload data associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first.',
            originalInstructions: 'The original files uploaded show here. It is possible to have one archive or many non archive files. Files should be data but all files are accepted'
        },
        {
            path: '/documentation_upload/',
            uploadType: 'docs',
            title: 'Upload Documentation',
            instructions: 'Upload documentation associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first.',
            originalInstructions: 'The original files uploaded show here. It is possible to have one archive or many non archive files. Files should be docs and only PDF, MarkDown, text and ReStructured text are accepted'
        },
    ];

    get version_number() {
        return this.$store.state.release.version_number;
    }

    get identifier() {
        return this.$store.state.release.codebase.identifier;
    }

    originals(uploadType: string) {
        return this.$store.state.files.originals[uploadType];
    }

    sip(uploadType: string) {
        return this.$store.state.files.sip[uploadType];
    }
}