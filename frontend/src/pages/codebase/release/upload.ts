import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import Vuex from 'vuex'
import {CodebaseReleaseAPI} from "api/index";
import {Upload} from "components/upload";
import * as _ from 'lodash';


const codebaseReleaseAPI = new CodebaseReleaseAPI();

Vue.use(Vuex);

interface File {
    label: string
}

interface Folder {
    label: string
    contents: Array<File | Folder>
}

@Component({
    name: 'c-file-tree',
    template: `<div>
        <div :style="indent">
            <i class="fa fa-folder-o"></i> {{ directory.label }}
            <div v-for="content in directory.contents">
                <div v-if="content.contents === undefined" :style="indent">
                    <i class="fa fa-file-o"></i> {{ content.label }}
                </div>
                <c-file-tree v-else :directory="content"></c-file-tree>
            </div>
        </div>
    </div>`
})
class FileTree extends Vue {
    @Prop()
    directory: Folder;

    get indent() {
        return { transform: `translate(50px)` };
    }
}


@Component(<any>{
    template: `<div>
            <p>
                Releases should include any code, documentation, input data and simulation results that would help
                someone else to understand the model. At least one code file is required.
            </p>
            <button class="btn btn-outline-secondary" @click="showPreview">Preview Download Package</button>
            <div class="modal fade" id="previewModal" tabindex="-1" role="dialog" aria-labelledby="previewModalLabel">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="previewModalLabel">Release File Download Preview</h5>
                            <button type="button" class="close" @click="closePreview" aria-label="Close">
                                <span aria-hidden="true" class="fa fa-times"></span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <span class="text-warning" v-if="folderContents === null">Loading download preview...</span>
                            <div class="alert alert-danger" v-else-if="folderContents.error !== undefined">
                                {{ folderContents.error }}
                            </div>
                            <c-file-tree :directory="folderContents" v-else></c-file-tree>
                        </div>
                    </div>
                </div>
            </div>
            <div v-for="config in configs">
                <c-upload :uploadType="config.uploadType" :acceptedFileTypes="config.acceptedFileTypes"
                    :instructions="config.instructions" :originalInstructions="config.originalInstructions" 
                    :originals="originals(config.uploadType)" :uploadUrl="uploadUrl(config.uploadType)"
                    :title="config.title" :key="config.uploadType"
                    @deleteFile="deleteFile(config.uploadType, $event)" @clear="clear(config.uploadType)"
                    @doneUpload="doneUpload(config.uploadType)">    
                </c-upload>
                <p v-if="config.description">{{ config.description }}</p>
            </div>
        </div>`,
    components: {
        'c-upload': Upload,
        'c-file-tree': FileTree
    }
})
export class UploadPage extends Vue {
    folderContents: Folder | { error: string } | null = null;

    configs = [
        {
            uploadType: 'code',
            acceptedFileTypes: '*/*',
            title: 'Upload Code',
            instructions: 'Upload code associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first.',
            originalInstructions: 'The original files uploaded show here. It is possible to have one archive or many non archive files. Files should be codebase related but all files are accepted',
            description: `Code associated with a release goes here. If you have your project in version control a 
                snapshot of the whole project should go in this folder as an archive.`
        },
        {
            uploadType: 'data',
            acceptedFileTypes: '*/*',
            title: 'Upload Data',
            instructions: 'Upload data associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first.',
            originalInstructions: 'The original files uploaded show here. It is possible to have one archive or many non archive files. Files should be data but all files are accepted'
        },
        {
            uploadType: 'docs',
            acceptedFileTypes: '*/*',
            title: 'Upload Documentation',
            instructions: 'Upload documentation associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first.',
            originalInstructions: 'The original files uploaded show here. It is possible to have one archive or many non archive files. Files should be docs and only PDF, MarkDown, text and ReStructured text are accepted'
        },
        {
            uploadType: 'results',
            acceptedFileTypes: '*/*',
            title: 'Upload Simulation Outputs',
            instructions: 'Upload simulation outputs associated with a project here. If an archive (zip or tar file) is uploaded it is extracted first.',
            originalInstructions: 'The original files uploaded show here. It is possible to have one archive or many non archive files. Files should be results but all files are accepted'
        }
    ];

    get version_number() {
        return this.$store.state.release.version_number;
    }

    get identifier() {
        return this.$store.state.release.codebase.identifier;
    }

    showPreview() {
        (<any>$)('#previewModal').modal('show');
        this.getDownloadPreview();
    }

    closePreview() {
        (<any>$)('#previewModal').modal('hide');
        this.folderContents = null;
    }

    async getDownloadPreview() {
        const response = await codebaseReleaseAPI
            .downloadPreview({ identifier: this.identifier, version_number: this.version_number});
        if (response.data) {
            this.folderContents = response.data;
        } else {
            this.folderContents =
                { error: response.response ? `HTTP Error (${response.response.status})`: 'Unknown Error' }
        }
    }

    originals(uploadType: string) {
        return this.$store.state.files.originals[uploadType];
    }

    uploadUrl(category) {
        return codebaseReleaseAPI.listOriginalsFileUrl({identifier: this.identifier,
            version_number: this.version_number, category})
    }

    doneUpload(uploadType: string) {
        return this.$store.dispatch('getOriginalFiles', uploadType);
    }

    deleteFile(uploadType: string, path: string) {
        this.$store.dispatch('deleteFile', {category: uploadType, path});
    }

    clear(uploadType: string) {
        this.$store.dispatch('clearCategory', {
            identifier: this.identifier, version_number: this.version_number,
            category: uploadType
        });
    }
}
