import { Component, Prop } from 'vue-property-decorator'
import * as Vue from 'vue'
import Vuex from 'vuex'
import { exposeComputed } from './store'
import * as _ from 'lodash'
import {codebaseReleaseAPI} from "api/index";

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
    msg: string
}

type UploadInfo = UploadSuccess | UploadProgress | UploadFailure;

@Component(<any>{
    template: `<div>
        <slot name="label"></slot>
        <div class="form-group">
            <input class="form-control-file" id="upload" type="file" @change="handleFiles($event)">
            <small class="form-text text-muted" v-if="instructions">{{ instructions }}</small>
        </div>
        <div>
            <div :class="fileUploadAlertClass(info)" v-for="(info, name) in fileUploadMsgs">
                <span v-if="info.kind === 'success'">
                    File {{ name }} uploaded sucessfully!
                </span>
                <span v-else-if="info.kind === 'progress'">
                    File upload {{ name }} is <b>{{ info.percentCompleted }}%</b> complete
                </span>
                <span v-else>
                    File upload failed
                </span>
            </div>
        </div>
        <div class="container">
            <div class="row" v-for="file in file_metadata.files">
                <div class="col-9"><a :href="file.url">{{ file.path }}</a></div>
                <div class="col-3"><button class="btn btn-sm btn-danger pull-right" @click="deleteFile(file.url)"><span class="fa fa-remove"></span></button></div>
            </div>
        </div>
    </div>`,
    computed: exposeComputed(['codebase.identifier', 'version_number'])
})
export default class Upload extends Vue {
    @Prop
    uploadType: string;

    fileUploadMsgs: { [name: string]: UploadInfo} = {};

    fileUploadAlertClass(uploadInfo: UploadInfo) {
        switch(uploadInfo.kind) {
            case 'success': return 'alert alert-success';
            case 'progress': return 'alert alert-secondary';
            case 'failure': return 'alert alert-danger';
        }
    }

    get uploadUrl() {
        return this.$store.state.files[this.uploadType].upload_url;
    }

    @Prop({ default: '' })
    instructions: string;

    @Prop({ default: '' })
    acceptedFileTypes: string;

    async handleFiles(event) {
        const file = event.target.files[0];
        const onUploadProgress = (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100)/progressEvent.total);
            this.$set(this.fileUploadMsgs, file.name, { kind: 'progress', percentCompleted, size: file.size});
        };
        const response = await codebaseReleaseAPI.uploadFile({ path: this.uploadUrl}, file, onUploadProgress);
        _.delay(() => this.$delete(this.fileUploadMsgs, file.name), 3000);
        await this.$store.dispatch('getFiles', this.uploadType);
        event.target.value = null;
    }

    get file_metadata() {
        return this.$store.state.files[this.uploadType];
    }

    set file_metadata(value) {
        this.$store.commit('setFiles', {upload_type: this.uploadType, value});
    }

    deleteFile(path: string) {
        this.$store.dispatch('deleteFile', {upload_type: this.uploadType, path});
    }
}