import * as Vue from 'vue'
import * as _ from 'lodash'
import {CodebaseReleaseAPI} from "api/index";
import {Component, Prop, Watch} from 'vue-property-decorator'
import Checkbox from '@/components/forms/checkbox'
import Datepicker from '@/components/forms/datepicker'
import Markdown from '@/components/forms/markdown'
import MessageDisplay from '@/components/message_display'
import TextArea from '@/components/forms/textarea'
import Input from '@/components/forms/input'
import Multiselect from 'vue-multiselect'
import Tagger from '@/components/tagger'
import * as yup from 'yup'
import {createFormValidator} from '@/pages/form'
import {HandlerShowSuccessMessage} from '@/api/handler'

const codebaseReleaseAPI = new CodebaseReleaseAPI();

export const schema = yup.object().shape({
    release_notes: yup.string().required().label('this'),
    embargo_end_date: yup.date().nullable().label('this'),
    os: yup.string().required().label('this'),
    platforms: yup.array().of(yup.object().shape({name: yup.string()})).min(1).required().label('this'),
    programming_languages: yup.array().of(yup.object().shape({name: yup.string()})).min(1).required().label('this'),
    live: yup.bool().label('this'),
    license: yup.object().shape({
        name: yup.string().required(),
        url: yup.string().url().required()
    }).required().label('this')
});

@Component(<any>{
    template: `<div>
        <p class='mt-3'>
            Detailed metadata helps others discover and reuse your computational models. Please take the time to
            document how to run your computational model, software and data dependencies, accepted inputs and expected
            outputs.
        </p>
        <c-markdown v-model="release_notes" :errorMsgs="errors.release_notes" name="releaseNotes" rows="3"
            label="Release Notes" :required="config.release_notes">
        </c-markdown>
        <c-datepicker v-model="embargo_end_date" :errorMsgs="errors.embargo_end_date" name="embargoEndDate" :clearButton="true"
            :required="config.embargo_end_date"
            label="Embargo End Date"
            help="The date your private release will be automatically made public">
        </c-datepicker>
        <div :class="['form-group', {'child-is-invalid': errors.os.length > 0}]">
            <label :class="['form-control-label', {'required': config.os}]">Operating System</label>
            <multiselect
                :value="osOption"
                @input="updateOs"
                name="os"
                :options="osOptions"
                placeholder="The operating system this model has been developed and tested on, e.g., Ubuntu, Mac, or Windows"
                label="display"
                track-by="name">
            </multiselect>
            <div v-if="errors.os.length > 0" class="invalid-feedback">{{ errors.os.join(', ') }}</div>
        </div>
        <c-tagger v-model="platforms" placeholder="Type to add platforms" :required="config.platforms"
            label="Software Framework(s)" help="Modeling software frameworks (e.g., NetLogo, RePast, Mason, CORMAS, Mesa) used by this model" :errorMsgs="errors.platforms">
        </c-tagger>
        <c-tagger v-model="programming_languages" placeholder="Type to add programming languages" :required="config.programming_languages"
            label="Programming Languages" help="Programming languages used in this model" :errorMsgs="errors.programming_languages">
        </c-tagger>
        <div :class="['form-group', {'child-is-invalid': errors.license.length > 0}]">
            <label :class="['form-control-label', {'required': config.license }]">License</label>
            <multiselect v-model="license" label="name" track-by="name" placeholder="Type to find license" :options="licenseOptions">
                <template slot="option" scope="props">
                    <div>
                         <a class='btn btn-sm btn-info' :href="props.option.url" target="_blank"><span class="fa fa-external-link"></span> view</a>
                         {{ props.option.name }}
                    </div>
                </template>
            </multiselect>
            <div v-if="errors.license.length > 0" class="invalid-feedback">a license must be selected</div>
            <small class="form-text text-muted">
            An open source licence to govern use and redistribution of your computational model.
            For more information about open source licenses, you may find the advice at
            <a target='_blank' href="//choosealicense.com">choosealicense.com</a> or
            <a target='_blank' href='//opensource.org/licenses'>opensource.org/licenses</a>
            helpful for deciding which license to use.
            </small>
        </div>
        <c-message-display :messages="statusMessages" @clear="statusMessages = []"/>
        <button type="button" class="btn btn-primary" @click="save">Save</button>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-datepicker': Datepicker,
        'c-input': Input,
        'c-markdown': Markdown,
        'c-message-display': MessageDisplay,
        'c-textarea': TextArea,
        'c-tagger': Tagger,
        Multiselect,
    },
})
export default class Detail extends createFormValidator(schema) {
    created() {
        (<any>this).state = this.$store.getters.detail;
    }

    get identity() {
        return this.$store.getters.identity;
    }

    message: string = '';

    get licenseOptions() {
        return this.$store.state.release.possible_licenses
    }

    osOptions = [
        {name: 'other', display: 'Other'},
        {name: 'linux', display: 'Unix/Linux'},
        {name: 'macos', display: 'Mac OS'},
        {name: 'windows', display: 'Windows'},
        {name: 'platform_independent', display: 'Operating System Independent'},
    ];
    matchingPlatforms = [];
    isLoadingPlatforms = false;

    matchingProgrammingLanguages = [{name: 'NetLogo'}, {name: 'Python'}];
    isLoadingProgrammingLanguages = false;

    get isPublished() {
        return this.$store.state.release.live;
    }

    get osOption() {
        return _.find(this.osOptions, (option) => option.name === this.state.os);
    }

    applyTextEdit(ev) {
        (<any>this).release_notes = ev.event.target.innerHTML;
    }

    updateOs(value) {
        (<any>this).os = value.name
    }

    updatePlatforms(value) {
        (<any>this).platforms = value.name
    }

    updateProgrammingLanguages(value) {
        (<any>this).programming_languages = value.name;
    }

    async save() {
        try {
            const {identifier, version_number} = this.identity;
            const self: any = this;
            await self.validate();
            const response = await codebaseReleaseAPI.updateDetail({
                identifier,
                version_number
            }, new HandlerShowSuccessMessage(this));
            await this.$store.dispatch('getCodebaseRelease', {identifier, version_number});
        } catch (e) {
            if (!(e instanceof yup.ValidationError)) {
                throw e;
            }
        }
    }
}
