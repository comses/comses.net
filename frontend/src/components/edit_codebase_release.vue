<template>
    <div>
        <!--<label class="form-control-label">Upload Release</label>
        <dropzone id="releaseUpload" acceptedFileTypes="image/*" :url="uploadReleaseURL" :headers="{'X-CSRFToken': csrftoken }" ref="release_upload" :useFontAwesome="true">
        </dropzone>-->
        <c-input name="decription" v-model="codebase_release.description">
            <label class="form-control-label" slot="label">Description</label>
        </c-input>
        <c-markdown name="documentation" v-model="codebase_release.documentation">
            <label class="form-control-label" slot="label">Documentation</label>
        </c-markdown>
        <c-input name="doi" v-model="codebase_release.doi">
            <label class="form-control-label" slot="label">DOI</label>
        </c-input>
        <c-datepicker name="embargo_end_date" v-model="codebase_release.embargo_end_date">
            <label class="form-control-label" slot="label">Embargo end date</label>
        </c-datepicker>
        <multiselect
            :value="codebase_release.license"
            @input="updateLicense"
            label="license"
            track-by="name"
            placeholder="Type to find license"
            :options="license_options">
            <template slot="option" scope="props">
                <div><a href="props.option.url">{{ props.option.name }}</a></div>
            </template>    
        </multiselect>
        <multiselect
            v-model="codebase_release.os"
            label="os"
            placeholder="Type to find os"
            :options="os_options">
        </multiselect>
        <c-input name="peer_reviewed" v-model="codebase_release.peer_reviewed" type="checkbox">
            <label class="form-control-label" slot="label">Peer Reviewed</label>
        </c-input>
        <c-edit-items :value="codebase_release.platforms" @create="codebase_release.platforms.push($event)" @remove="codebase_release.platforms.splice($event, 1)" @modify="codebase_release.platforms.splice($event, 1, $event.value)" name="platforms" placeholder="Add platform">
            <label class="form-control-label" slot="label">Platforms</label>
        </c-edit-items>
        <c-edit-items :value="codebase_release.programming_languages" @create="codebase_release.programming_languages.push($event)" @remove="codebase_release.programming_languages.splice($event, 1)" @modify="codebase_release.programming_languages.splice($event, 1, $event.value)" name="programming_languages" placeholder="Add programming language">
            <label class="form-control-label" slot="label">Programming Languages</label>
        </c-edit-items>
        <c-input name="submitter" v-model="codebase_release.submitter">
            <label class="form-control-label" slot="label">Submitter</label>
        </c-input>
        <c-input name="version" v-model="codebase_release.version">
            <label class="form-control-label" slot="label">Version</label>
        </c-input>
    </div>
</template>
<script lang="ts">
import * as Vue from 'vue'
import { Component, Prop } from 'vue-property-decorator'
import * as draggable from 'vuedraggable'
import { CodebaseRelease } from 'store/common'
import EditItems from 'components/edit_items.vue'
import Input from 'components/forms/input.vue'
import Datepicker from 'components/forms/datepicker.vue';
import Markdown from 'components/forms/markdown.vue'
import Multiselect from 'vue-multiselect'
import * as Dropzone from 'vue2-dropzone'

/*
 * codebase_contributors, dependencies, description, documentation, doi, download_count, embargo_end_date, license, os, peer_reviewed, platforms, programming_languages, submitted_package, submitter, version_number
 */
@Component({
    components: {
        'c-datepicker': Datepicker,
        'c-edit-items': EditItems,
        'c-input': Input,
        'c-markdown': Markdown,
        draggable
    }
})
export default class EditTextList extends Vue {
    @Prop
    codebase_release: CodebaseRelease;

    license_options: Array<{ name: string, url: string}> = [
        { name: 'Library GPL', url: 'https://opensource.org/licenses/lgpl-license'}, 
        { name: 'GPL V2', url: 'https://opensource.org/licenses/gpl-license'}, 
        { name: 'GPL V3', url: 'https://opensource.org/licenses/gpl-license'}, 
        { name: 'MIT', url: 'https://opensource.org/licenses/MIT'}, 
        { name: 'Apache 2.0', url: 'https://opensource.org/licenses/Apache-2.0'},
        { name: 'BSD 3-Clause', url: 'https://opensource.org/licenses/BSD-3-Clause'},
        { name: 'BSD 2-Clause', url: 'https://opensource.org/licenses/BSD-2-Clause'}
    ];

    os_options: Array<string> = ['Windows', 'Mac OS X', 'Linux'];

    updateLicense(license_option: { name: string, url: string}) {
        this.codebase_release.license = license_option.name;
    }

}
</script>
