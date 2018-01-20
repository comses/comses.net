import {Component} from 'vue-property-decorator'
import Vue from 'vue'
import Vuex from 'vuex'
import {CodebaseReleaseAPI} from "api/index";
import {Upload} from "components/upload";


const codebaseReleaseAPI = new CodebaseReleaseAPI();

Vue.use(Vuex);


@Component(<any>{
    template: `<div>
            <p>
                Releases should include any code, documentation, input data and simulation results that would help
                someone else to understand the model. At least one code file is required.
            </p>
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
        'c-upload': Upload
    }
})
export class UploadPage extends Vue {
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

    originals(uploadType: string) {
        return this.$store.state.files.originals[uploadType];
    }

    uploadUrl(category) {
        return codebaseReleaseAPI.listOriginalsFileUrl({identifier: this.identifier,
            version_number: this.version_number, category})
    }

    doneUpload(uploadType: string) {
        return Promise.all([
            this.$store.dispatch('getOriginalFiles', uploadType),
            this.$store.dispatch('getSipFiles', uploadType)
        ]);
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
