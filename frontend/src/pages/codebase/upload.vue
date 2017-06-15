<template>
    <div>
        <slot name="label"></slot>
        <dropzone id="releaseUpload" :acceptedFileTypes="acceptedFileTypes" 
            :url="uploadUrl" :headers="{'X-CSRFToken': csrftoken }" :useFontAwesome="true">
        </dropzone>
    </div>
</template>

<script lang="ts">
import { Component, Prop } from 'vue-property-decorator'
import * as queryString from 'query-string'
import * as Dropzone from 'vue2-dropzone'
import * as Vue from 'vue'
import { getCookie } from '../../api/index'
import { CodebaseRelease } from '../../store/common'

@Component({
    components: {
        Dropzone
    }
})
export default class Upload extends Vue {
    @Prop
    uploadUrl: string;

    @Prop({ default: "*/*"})
    acceptedFileTypes: string;

    get csrftoken() {
        return getCookie('csrftoken');
    }
}
</script>