import { Component, Prop } from 'vue-property-decorator'
import * as queryString from 'query-string'
import * as Dropzone from 'vue2-dropzone'
import * as Vue from 'vue'
import Vuex from 'vuex'
import { getCookie } from 'api/index'
import { CodebaseRelease } from 'store/common'
import { exposeComputed } from './store'
import { upperFirst } from 'lodash'

Vue.use(Vuex);

@Component(<any>{
    template: `<div>
        <slot name="label"></slot>
        <!--<input id="upload" type="file" multiple>-->
        <dropzone id="releaseUpload" :acceptedFileTypes="acceptedFileTypes" :url="uploadUrl" :headers="{'X-CSRFToken': csrftoken }" :useFontAwesome="true"
            @vdropzone-success="addFile" ref="uploader" @vdropzone-sending="updateUploadUrl">
        </dropzone>
        <small class="form-text text-muted" v-if="instructions">{{ instructions }}</small>
        <div class="container">
            <div class="row" v-for="file in file_metadata.files">
                <div class="col-9"><a :href="file.url">{{ file.path }}</a></div>
                <div class="col-3"><button class="btn btn-sm btn-danger pull-right" @click="deleteFile(file.url)"><span class="fa fa-remove"></span></button></div>
            </div>
        </div>
    </div>`,
    components: {
        Dropzone
    },
    computed: exposeComputed(['codebase.identifier', 'version_number'])
})
export default class Upload extends Vue {
    @Prop
    uploadType: string;

    get hasLoaded(): boolean {
        // exists to get around a bug in vue-dropzone where computed urls only use their first value
        return this.$store.state.files[this.uploadType].upload_url !== '';
    }

    get uploadUrl() {
        return this.$store.state.files[this.uploadType].upload_url;
    }

    @Prop({ default: '' })
    instructions: string;

    @Prop({ default: "" })
    acceptedFileTypes: string;

    get csrftoken() {
        return getCookie('csrftoken');
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

    addFile(event) {
        console.log(event);
        this.$store.dispatch('getFiles', this.uploadType);
    }

    updateUploadUrl(file, xhr, formData) {
        console.log({uploader: this.$refs.uploader});
        (<any>this.$refs.uploader).setOption('url', this.uploadUrl);
        console.log({file, xhr, formData});
    }
}