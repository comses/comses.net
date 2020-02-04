import * as _ from 'lodash';
import {CodebaseReleaseAPI} from '@/api';
import {Component, Prop, Watch} from 'vue-property-decorator';
import Checkbox from '@/components/forms/checkbox';
import Datepicker from '@/components/forms/DatePicker.vue';
import Markdown from '@/components/forms/markdown';
import MessageDisplay from '@/components/message_display';
import TextArea from '@/components/forms/textarea';
import Input from '@/components/forms/input';
import Multiselect from 'vue-multiselect';
import Tagger from '@/components/tagger';
import * as yup from 'yup';
import {createFormValidator} from '@/pages/form';
import {HandlerShowSuccessMessage} from '@/api/handler';

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
        url: yup.string().url().required(),
    }).required().label('this'),
});

@Component({
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
                placeholder="The operating system(s) this model is compatible with, e.g., Linux, macOS, Windows"
                label="display"
                track-by="name">
            </multiselect>
            <div v-if="errors.os.length > 0" class="invalid-feedback">{{ errors.os.join(', ') }}</div>
        </div>
        <c-tagger v-model="platforms" placeholder="Software frameworks used by this model" :required="false"
            label="Software Framework(s)" help="Modeling software frameworks (e.g., NetLogo, RePast, Mason, CORMAS, Mesa, etc.) used by this model" :errorMsgs="errors.platforms">
        </c-tagger>
        <c-tagger v-model="programming_languages" placeholder="Programming languages used by this model" :required="config.programming_languages"
            label="Programming Languages" help="Programming languages used in this model" :errorMsgs="errors.programming_languages">
        </c-tagger>
        <div :class="['form-group', {'child-is-invalid': errors.license.length > 0}]">
            <label :class="['form-control-label', {'required': config.license }]">License</label>
            <multiselect v-model="license" label="name" track-by="name" placeholder="Type to find license" :options="licenseOptions">
                <template slot="option" slot-scope="props">
                    <div>
                         <a class='btn btn-sm btn-info' :href="props.option.url" target="_blank"><span class="fas fa-external-link-alt"></span> view</a>
                         {{ props.option.name }}
                    </div>
                </template>
            </multiselect>
            <div v-if="errors.license.length > 0" class="invalid-feedback">a license must be selected</div>
            <small class="form-text text-muted">
            An open source licence to govern use and redistribution of your computational model. For more information
            and advice about picking an open source license, please check out
            <a target='_blank' href="//choosealicense.com">choosealicense.com</a> or
            <a target='_blank' href='//opensource.org/licenses'>opensource.org/licenses</a>.
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
} as any)
export default class Detail extends createFormValidator(schema) {

    get identity() {
        return this.$store.getters.identity;
    }

    get licenseOptions() {
        return this.$store.state.release.possible_licenses;
    }

    get isPublished() {
        return this.$store.state.release.live;
    }

    get osOption() {
        return _.find(this.osOptions, (option) => option.name === this.state.os);
    }

    public message: string = '';

    public osOptions = [
        {name: 'other', display: 'Other'},
        {name: 'linux', display: 'Unix/Linux'},
        {name: 'macos', display: 'Mac OS'},
        {name: 'windows', display: 'Windows'},
        {name: 'platform_independent', display: 'Operating System Independent'},
    ];
    public matchingPlatforms = [];
    public isLoadingPlatforms = false;

    public matchingProgrammingLanguages = [{name: 'NetLogo'}, {name: 'Python'}];
    public isLoadingProgrammingLanguages = false;
    public created() {
        (this as any).state = this.$store.getters.detail;
    }

    public applyTextEdit(ev) {
        (this as any).release_notes = ev.event.target.innerHTML;
    }

    public updateOs(value) {
        (this as any).os = value.name;
    }

    public updatePlatforms(value) {
        (this as any).platforms = value.name;
    }

    public updateProgrammingLanguages(value) {
        (this as any).programming_languages = value.name;
    }

    public async save() {
        try {
            const {identifier, version_number} = this.identity;
            const self: any = this;
            await self.validate();
            const response = await codebaseReleaseAPI.updateDetail({
                identifier,
                version_number,
            }, new HandlerShowSuccessMessage(this));
            await this.$store.dispatch('getCodebaseRelease', {identifier, version_number});
        } catch (e) {
            if (!(e instanceof yup.ValidationError)) {
                throw e;
            }
        }
    }
}
