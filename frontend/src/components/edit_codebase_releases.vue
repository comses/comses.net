<template>
    <div class="container">
        <div class="row">
            <div class="col-sm-12 col-md-6">Releases</div>
            <div class="col-sm-12 col-md-6">
                <label class="form-control-label">Upload Release</label>
                <dropzone id="releaseUpload" acceptedFileTypes="image/*" :url="uploadReleaseURL" :headers="{'X-CSRFToken': csrftoken }" ref="release_upload" :useFontAwesome="true">
                </dropzone>
            </div>
        </div>
        <div class="row">
            <div class="list-group">
                <div class="list-group-item" v-for="release in codebase_releases">Version: {{ release.version_number }} DOI: {{ release.doi || 'None'}}</div>
            </div>
        </div>
    </div>
</template>
<script lang="ts">
import { Component, Prop } from 'vue-property-decorator'
import * as queryString from 'query-string'
import * as Dropzone from 'vue2-dropzone'
import * as Vue from 'vue'
import { getCookie } from '../api/index'
import { CodebaseRelease } from '../store/common'

@Component({
    components: {
        Dropzone
    }
})
export default class EditCodebaseReleases extends Vue {
    @Prop
    codebase_identifier: string

    @Prop
    codebase_releases: Array<CodebaseRelease>;

    get csrftoken() {
        // console.log(getCookie('csrftoken'));
        return getCookie('csrftoken');
    }

    get uploadReleaseURL() {
        return `${window.location.href}create_release/`;
    }
}
</script>

