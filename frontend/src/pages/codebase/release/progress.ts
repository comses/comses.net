import Vue from 'vue'
import {Component, Prop} from 'vue-property-decorator'
import {schema} from './detail'
import * as _ from 'lodash';
import {populateErrorsFromValidationError} from 'pages/form'

@Component({
    template: `<p class="card-text">
        {{ label }}: 
        <span v-if="check" class="fa fa-check text-success"></span>
        <span v-else class="fa fa-times text-danger"></span> 
    </p>`

})
export class Check extends Vue {
    @Prop()
    check: boolean;

    @Prop()
    label: string;
}

@Component({
    template: `<div class="container-fluid px-0">
        <div class="row">
            <div class="col-sm-12 col-md-6 col-lg-4" v-if="!published">
                <div class="card">
                    <div class="card-header">
                        Upload
                    </div>
                    <div class="card-body">
                        <p class="card-text">
                            <c-check label="At least one code file" :check="uploadProgress.code"></c-check>
                            <c-check label="At least one doc file (optional)" :check="uploadProgress.docs"></c-check>
                            <c-check label="At least one data file (optional)" :check="uploadProgress.data"></c-check>
                            <c-check label="At least one result file (optional)" :check="uploadProgress.results"></c-check>
                        </p>
                    </div>
                </div>
            </div>
            <div :class="cardClass">
                <div class="card">
                    <div class="card-header">
                        Contributors
                    </div>
                    <div class="card-body">
                        <c-check label="More than one contributor" :check="contributorProgress"></c-check>
                    </div>
                </div>
            </div>
            <div :class="cardClass">
                <div class="card">
                    <div class="card-header">
                        Detail
                    </div>
                    <div class="card-body">
                        <c-check label="Release note done" :check="detailProgress.release_notes"></c-check>
                        <c-check label="Operating system selected" :check="detailProgress.os"></c-check>
                        <c-check label="Platforms selected" :check="detailProgress.platforms"></c-check>
                        <c-check label="Languages selected" :check="detailProgress.programming_languages"></c-check>
                        <c-check label="License chosen" :check="detailProgress.license"></c-check> 
                    </div>
                </div>
            </div>
        </div>
    </div>`,
    components: {
        'c-check': Check
    }
})
export class Progress extends Vue {
    get cardClass() {
        // Published releases stretch contributor and detail cards to take up whole row
        return ['col-sm-12 col-md-6', { 'col-lg-4': !this.published }]
    }

    get published() {
        return this.$store.state.release.live;
    }

    get detail() {
        return this.$store.getters.detail;
    }

    get upload() {
        return this.$store.state.files.originals;
    }

    get contributors() {
        return this.$store.state.release.release_contributors;
    }

    get detailProgress() {
        return _.mapValues(this.detail, (value, key, obj) => !_.isEmpty(value) || key === 'embargo_end_date');
    }

    get uploadProgress() {
        return {
            code: this.upload.code.length > 0,
            data: this.upload.data.length > 0,
            docs: this.upload.data.length > 0,
            results: this.upload.results.length > 0
        };
    }

    get contributorProgress() {
        return this.contributors.length > 0;
    }
}