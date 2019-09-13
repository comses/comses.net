import {Component, Prop} from 'vue-property-decorator';
import Vue from 'vue';
import Vuex from 'vuex';
import {CodebaseReleaseAPI} from '@/api/index';
import {Upload} from '@/components/upload';
import * as _ from 'lodash';


const codebaseReleaseAPI = new CodebaseReleaseAPI();

Vue.use(Vuex);

interface File {
    label: string;
}

interface Folder {
    label: string;
    contents: Array<File | Folder>;
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
    </div>`,
})
class FileTree extends Vue {
    @Prop()
    public directory: Folder;

    get indent() {
        return { transform: `translate(50px)` };
    }
}


@Component({
    template: `<div>
            <p class='mt-3'>
                A codebase release should ideally include the source code, documentation, input data and dependencies necessary for
                someone else (including your future self) to understand, replicate, or reuse the model. Please note that we impose a
                specific directory structure to organize your uploaded files - you can view the active filesystem layout below.
                Source code is placed in <code>project-root/code/</code>, data files are placed in <code>project-root/data/</code>,
                and documentation files are placed in <code>project-root/docs/</code>, and simulation outputs are placed in
                <code>project-root/results/</code>.
                This means that if your source code has references to your uploaded data files you should consider using the relative path
                <code>../data/&lt;datafile&gt;</code> to access those data files. This will make the lives of others
                wishing to review, download and run your model easier.
            </p>
            <div class="card card-body bg-light">
                <h3 class='card-title'>Current Archival Package Filesystem Layout</h3>
                <span class="text-warning" v-if="folderContents === null">Loading download preview...</span>
                <div class="alert alert-danger" v-else-if="folderContents.error !== undefined">
                    {{ folderContents.error }}
                </div>
                <c-file-tree :directory="folderContents" v-else></c-file-tree>
            </div>
            <div v-for="config in configs">
                <c-upload :uploadType="config.uploadType" :acceptedFileTypes="config.acceptedFileTypes"
                    :instructions="config.instructions" :originalInstructions="config.originalInstructions"
                    :originals="originals(config.uploadType)" :uploadUrl="uploadUrl(config.uploadType)"
                    :title="config.title" :key="config.uploadType"
                    @deleteFile="deleteFile(config.uploadType, $event)" @clear="clear(config.uploadType)"
                    @doneUpload="doneUpload(config.uploadType)">
                </c-upload>
                <hr>
            </div>
        </div>`,
    components: {
        'c-upload': Upload,
        'c-file-tree': FileTree,
    },
} as any)
export class UploadPage extends Vue {
    public folderContents: Folder | { error: string } | null = null;

    public configs = [
        {
            uploadType: 'code',
            acceptedFileTypes: '*/*',
            title: 'Upload Source Code (required)',
            instructions: `You can upload a single plaintext source file (e.g., a NetLogo .nlogo file) or a tar or zip archive of
            plaintext source code representing your codebase. Archives will be unpacked and extracted as part of archival processing
            and system files will be removed but the archive's directory structure is preserved.  All file types are currently
            accepted though files should be stored in open or plaintext formats. We may remove executables or binaries in the
            future.`,
            originalInstructions: 'Submitted source code file(s) to be placed in <project-root>/code/',
        },
        {
            uploadType: 'docs',
            acceptedFileTypes: '*/*',
            title: 'Upload Narrative Documentation (required)',
            instructions: `Upload narrative documentation that comprehensively describes your computational model. The ODD
            Protocol offers a good starting point for thinking about how to comprehensively describe agent based models and
            good Narrative Documentation often includes equations, pseudocode, and flow diagrams. Acceptable files include
            plain text formats (including Markdown and other structured text), OpenDocument Text files (ODT), and PDF documents.`,
            originalInstructions: 'Submitted narrative documentation file(s) to be placed in <project-root>/docs/',
        },
        {
            uploadType: 'data',
            acceptedFileTypes: '*/*',
            title: 'Upload Data (optional)',
            instructions: `Upload any datasets required by your source code. There is a limit on file upload size so if
            your datasets are very large, you may consider using osf.io or figshare or other data repository to store your
            data and refer to it in your code via DOI or other permanent URL. If a zip or tar archive is uploaded
            it will be automatically unpacked. Files should be plaintext or an open data formats but all file types
            are currently accepted. Please note that data files uploaded here will be placed in a "<project-root>/data"
            directory so if you'd like for your source code to work immediately when another researcher downloads your
            codebase, please consider referring to any input data files via a relative path "../data/<your-data-file>".`,
            originalInstructions: 'Submitted data file(s) to be placed in <project-root>/data/',
        },
        {
            uploadType: 'results',
            acceptedFileTypes: '*/*',
            title: 'Upload Simulation Outputs (optional)',
            instructions: 'Upload simulation outputs associated with your computational model. Ideally these data files should be in plain text or other open data formats.',
            originalInstructions: 'Submitted model output file(s) to be placed in <project-root>/results/',
        },
    ];

    get version_number() {
        return this.$store.state.release.version_number;
    }

    get identifier() {
        return this.$store.state.release.codebase.identifier;
    }

    public created() {
        this.getDownloadPreview();
    }

    public async getDownloadPreview() {
        const response = await codebaseReleaseAPI.downloadPreview(
            { identifier: this.identifier, version_number: this.version_number},
        );
        if (response.data) {
            this.folderContents = response.data;
        } else {
            this.folderContents = { error: response.response ? `HTTP Error (${response.response.status})` : 'Unknown Error' };
        }
    }

    public originals(uploadType: string) {
        return this.$store.state.files.originals[uploadType];
    }

    public uploadUrl(category) {
        return codebaseReleaseAPI.listOriginalsFileUrl({identifier: this.identifier,
            version_number: this.version_number, category});
    }

    public doneUpload(uploadType: string) {
        this.getDownloadPreview();
        return this.$store.dispatch('getOriginalFiles', uploadType);
    }

    public deleteFile(uploadType: string, path: string) {
        this.getDownloadPreview();
        this.$store.dispatch('deleteFile', {category: uploadType, path});
    }

    public clear(uploadType: string) {
        this.getDownloadPreview();
        this.$store.dispatch('clearCategory', {
            identifier: this.identifier, version_number: this.version_number,
            category: uploadType,
        });
    }
}
