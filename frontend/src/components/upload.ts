import {Component, Prop} from 'vue-property-decorator';
import {api} from '@/api/connection';
import Vue from 'vue';
import * as _ from 'lodash';

interface UploadSuccess {
    kind: 'success';
    msg: string;
}

interface UploadProgress {
    kind: 'progress';
    percentCompleted: number;
    size: number;
}

interface UploadFailure {
    kind: 'failure';
    msgs: Array<{ level: string, msg: { detail: string, stage: string } }>;
}

type UploadInfo = UploadSuccess | UploadProgress | UploadFailure;

@Component({
    template: `<div>
        <h3 class="mt-4">{{ title }}</h3>
        <slot name="label"></slot>
        <div class="text-muted" v-if="instructions">{{ instructions }}</div>
        <div class="d-flex justify-content-between">
            <div>
                <label :for="uploadId"><div class="btn btn-primary">Upload a file</div></label>
                <input class="invisible" :id="uploadId" type="file"
                       @change="handleFiles($event)" :accept="acceptedFileTypes">
            </div>
            <div>
                <button class="btn btn-danger" @click="clear">Remove all files</button>
            </div>
        </div>
        <div>
            <div class="alert alert-secondary" v-for="(info, name) in fileUploadProgressMsgs">
                File upload {{ name }} is <b>{{ info.percentCompleted }}%</b> complete
            </div>
            <div class="alert alert-danger alert-dismissable" v-if="hasErrors">
                <button class="close" aria-label="Close" @click="clearUploadErrors">
                    <span aria-hidden="true"><span class="fas fa-window-close"></span></span>
                </button>
                <div v-if="fileUploadErrorMsgs.detail">
                   {{ fileUploadErrorMsgs.detail }}
                </div>
                <div v-for="(error, name) in fileUploadErrorMsgs" v-else>
                    <div v-for="msg in error.msgs"><b>{{ displayStage(msg.msg.stage) }}</b>: {{ msg.msg.detail }}</div>
                </div>
            </div>
        </div>
        <div class="list-group" v-if="originals.length > 0">
            <small class="form-text text-muted">
                {{ originalInstructions }}
            </small>
            <div class="list-group-item d-flex justify-content-between align-items-center" v-for="file in originals">
                {{ file.name }}
                <button class="btn btn-sm btn-danger pull-right" @click="deleteFile(file.identifier)">
                    <span class="fas fa-trash-alt"></span>
                </button>
            </div>
        </div>
        <div class='alert alert-info' v-else>
            No files uploaded
        </div>
    </div>`,
} as any)
export class Upload extends Vue {
    @Prop()
    public uploadUrl: string;

    public fileUploadErrorMsgs: { [name: string]: UploadInfo } = {};
    public fileUploadProgressMsgs: { [name: string]: UploadProgress } = {};

    @Prop()
    public title: string;

    @Prop({default: ''})
    public instructions: string;

    @Prop({default: ''})
    public acceptedFileTypes: string;

    @Prop({default: ''})
    public originalInstructions: string;

    @Prop()
    public originals: any[];

    get uploadId() {
        return `upload_${_.uniqueId()}`;
    }

    public displayStage(stage) {
        if (stage === 'sip') {
            return 'During archive unpack';
        } else {
            return 'During upload';
        }
    }

    public async handleFiles(event) {
        const file = event.target.files[0];
        const formData = new FormData();
        formData.append('file', file);

        const onUploadProgress = (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            this.$set(this.fileUploadProgressMsgs, file.name, {kind: 'progress', percentCompleted, size: file.size});
        };
        _.delay(() => this.$delete(this.fileUploadProgressMsgs, file.name), 6000);
        try {
            await api.postForm(this.uploadUrl, formData,
                {headers: {'Content-Type': 'multipart/form-data'}, onUploadProgress});
        } catch (error) {
            if (error.response) {
                const response = error.response;
                if (response.data.detail) {
                    this.fileUploadErrorMsgs = response.data;
                }
                this.$set(this.fileUploadErrorMsgs, file.name, {kind: 'failure', msgs: error.response.data});
            }
        }
        event.target.value = null;
        this.$emit('doneUpload');
    }

    public clearUploadErrors() {
        this.fileUploadErrorMsgs = {};
    }

    get hasErrors() {
        return !_.isEmpty(this.fileUploadErrorMsgs);
    }

    public deleteFile(identifier: string) {
        this.$emit('deleteFile', identifier);
    }

    public clear() {
        this.$emit('clear');
    }
}
