import * as Vue from 'vue'
import * as _ from 'lodash'
import {codebaseReleaseAPI} from "api/index";
import {Component, Prop, Watch} from 'vue-property-decorator'
import Checkbox from 'components/forms/checkbox'
import Datepicker from 'components/forms/datepicker'
import Markdown from 'components/forms/markdown'
import MessageDisplay from 'components/message_display'
import TextArea from 'components/forms/textarea'
import Input from 'components/forms/input'
import Multiselect from 'vue-multiselect'
import Tagger from 'components/tagger'
import * as yup from 'yup'
import {createFormValidator} from 'pages/form'
import {HandlerShowSuccessMessage} from 'api/handler'

const schema = yup.object().shape({
    description: yup.string().required().label('this'),
    embargo_end_date: yup.date().nullable().label('this'),
    os: yup.string().required().label('this'),
    platforms: yup.array().of(yup.object().shape({name: yup.string()})).min(1).label('this'),
    programming_languages: yup.array().of(yup.object().shape({name: yup.string()})).min(1).label('this'),
    live: yup.bool().label('this'),
    license: yup.object().shape({
        name: yup.string().required(),
        url: yup.string().url().required()
    }).label('this')
});

@Component(<any>{
    template: `<div>
        <c-markdown v-model="description" :errorMsgs="errors.description" name="description" rows="3" label="Description">
        </c-markdown>
        <c-datepicker v-model="embargo_end_date" :errorMsgs="errors.embargo_end_date" name="embargoEndDate" :clearButton="true">
            <label class="form-control-label" slot="label">Embargo End Date</label>
            <small class="form-text text-muted" slot="help">The date your release is automatically published</small>
        </c-datepicker>
        <div :class="['form-group', {'child-is-invalid': errors.os.length > 0}]">
            <label class="form-control-label">Operating System</label>
            <multiselect 
                :value="osOption"
                @input="updateOs"
                name="os" 
                :options="osOptions" 
                placeholder="Pick the OS the model runs on"
                label="display"
                track-by="name">
            </multiselect>
            <div v-if="errors.os.length > 0" class="invalid-feedback">{{ errors.os.join(', ') }}</div>
        </div>
        <c-tagger v-model="platforms" placeholder="Type to add platforms" 
            label="Platforms" help="Platforms used in this model" :errorMsgs="errors.platforms">
        </c-tagger>
        <c-tagger v-model="programming_languages" placeholder="Type to add programming languages" 
            label="Programming Languages" help="Programming languages used in this model" :errorMsgs="errors.programming_languages">
        </c-tagger>
        <div class="form-group" v-if="!isPublished">
            <c-checkbox name="live" v-model="live" label="Published?">
                <small class="form-text text-muted" slot="help">Published models are visible to everyone. Unpublished models are visible only to you.
                    Once a model has been published files associated with the release cannot be added, modified or deleted.
                </small>
            </c-checkbox>
        </div>
        <div :class="['form-group', {'child-is-invalid': errors.license.length > 0}]">
            <multiselect v-model="license" label="name" track-by="name" placeholder="Type to find license" :options="licenseOptions">
                <template slot="option" scope="props">
                    <div>
                        {{ props.option.name }} <a :href="props.option.url" target="_blank"><span class="fa fa-external-link"></span></a>
                    </div>
                </template>
            </multiselect>
            <div v-if="errors.license.length > 0" class="invalid-feedback">a license must be selected</div>
            <small class="form-text text-muted">A software licence is a document governing use and redistribution of your model</small>
        </div>
        <c-message-display :messages="statusMessages"/>
        <button type="button" v-show="!isDirty" class="btn btn-primary" @click="save">Save</button>
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
export default class Description extends createFormValidator(schema) {
    created() {
        (<any>this).state = this.$store.getters.detail;
    }

    get identity() {
        return this.$store.getters.identity;
    }

    isDirty = false;

    message: string = '';

    licenseOptions: Array<{ name: string, url: string }> = [
        { name: 'Library GPL', url: 'https://www.gnu.org/licenses/lgpl.html' },
        { name: 'GPL V2', url: 'https://www.gnu.org/licenses/gpl-2.0.en.html' },
        { name: 'GPL V3', url: 'https://www.gnu.org/licenses/gpl-3.0.en.html' },
        { name: 'MIT', url: 'https://opensource.org/licenses/MIT' },
        { name: 'Apache 2.0', url: 'https://opensource.org/licenses/Apache-2.0' },
        { name: 'BSD 3-Clause', url: 'https://opensource.org/licenses/BSD-3-Clause' },
        { name: 'BSD 2-Clause', url: 'https://opensource.org/licenses/BSD-2-Clause' }
    ];

    osOptions = [
        { name: 'other', display: 'Other' },
        { name: 'linux', display: 'Unix/Linux' },
        { name: 'macos', display: 'Mac OS' },
        { name: 'windows', display: 'Windows' },
        { name: 'platform_independent', display: 'Platform Independent' },
    ];
    matchingPlatforms = [];
    isLoadingPlatforms = false;

    matchingProgrammingLanguages = [{ name: 'NetLogo' }, { name: 'Python'}];
    isLoadingProgrammingLanguages = false;

    get isPublished() {
        return this.$store.state.release.live;
    }

    get osOption() {
        return _.find(this.osOptions, (option) => option.name === this.state.os);
    }

    applyTextEdit(ev) {
        (<any>this).description = ev.event.target.innerHTML;
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
        const { identifier, version_number } = this.identity;
        const self: any = this;
        await self.validate();
        const response = await codebaseReleaseAPI.updateDetail({
            identifier,
            version_number
        }, new HandlerShowSuccessMessage(this));
        await this.$store.dispatch('getCodebaseRelease', {identifier, version_number});
    }
}