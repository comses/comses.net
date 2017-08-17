import * as Vue from 'vue'
import * as _ from 'lodash'
import { api_base } from 'api'
import { Component, Prop, Watch} from 'vue-property-decorator'
import Checkbox from 'components/forms/checkbox'
import Datepicker from 'components/forms/datepicker'
import Markdown from 'components/forms/markdown'
import TextArea from 'components/forms/textarea'
import Input from 'components/forms/input'
import Multiselect from 'vue-multiselect'
import Tagger from 'components/tagger'
import { exposeComputed } from './store'
import * as yup from 'yup'

const schema = yup.object().shape({
    description: yup.string().required().label('this'),
    embargo_end_date: yup.date().nullable().label('this'),
    os: yup.string().required().label('this'),
    platforms: yup.array().of(yup.object().shape({ name: yup.string()})).min(1).label('this'),
    programming_languages: yup.array().of(yup.object().shape({ name: yup.string()})).min(1).label('this'),
    live: yup.bool().label('this'),
    license: yup.object().shape({
        name: yup.string().required(),
        url: yup.string().url().required()
    }).label('this')
});

function validate(self, field_name, value) {
    yup.reach(schema, field_name).validate(value)
        .then(value => self.errors[field_name] = [])
        .catch(ve => { 
            self.errors[field_name] = ve.errors
        });
}

@Component(<any>{
    template: `<div>
        <c-textarea v-model="state.description" :errorMsgs="errors.description" name="description" rows="3" label="Description">
        </c-textarea>
        <c-datepicker v-model="state.embargo_end_Date" :errorMsgs="errors.embargo_end_date" name="embargoEndDate" :clearButton="true">
            <label class="form-control-label" slot="label">Embargo End Date</label>
            <small class="form-text text-muted" slot="help">The date your release is automatically published</small>
        </c-datepicker>
        <div class="form-group">
            <label class="form-control-label">Operating System</label>
            <multiselect 
                :value="state.os"
                @input="updateOs"
                name="os" 
                :options="osOptions" 
                placeholder="Pick the OS the model runs on"
                label="display"
                track-by="name">
            </multiselect>
        </div>
        <c-tagger v-model="state.platforms" placeholder="Type to add platforms" 
            label="Platforms" help="Platforms used in this model" :errorMsgs="errors.platforms">
        </c-tagger>
        <c-tagger v-model="state.programming_languages" placeholder="Type to add programming languages" 
            label="Programming Languages" help="Programming languages used in this model" :errorMsgs="errors.programming_languages">
        </c-tagger>
        <div class="form-group">
            <c-checkbox name="live" v-model="state.live" label="Published?">
                <small class="form-text text-muted" slot="help">Published models are visible to everyone. Unpublished models are visible only to you</small>
            </c-checkbox>
        </div>
        <div :class="['form-group', {'has-danger': errors.license.length > 0}]">
            <multiselect v-model="state.license" label="name" track-by="name" placeholder="Type to find license" :options="licenseOptions">
                <template slot="option" scope="props">
                    <div>
                        {{ props.option.name }} <a :href="props.option.url" target="_blank"><span class="fa fa-external-link"></span></a>
                    </div>
                </template>
            </multiselect>
            <div v-if="errors.license > 0" class="form-control-feedback">{{ errors.license.join(', ') }}</div>
            <small class="form-text text-muted">A software licence is a document governing use and redistribution of your model</small>
        </div>
        <button type="button" v-show="!isDirty" class="btn btn-primary" @click="save">Save</button>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-datepicker': Datepicker,
        'c-input': Input,
        'c-markdown': Markdown,
        'c-textarea': TextArea,
        'c-tagger': Tagger,
        Multiselect
    }
})
export default class Description extends Vue {
    @Prop
    initialData: object;

    mounted() {
        this.state = <any>_.merge({}, this.initialData);
    }

    get identity() {
        return this.$store.getters.identity;
    }
    isDirty = false;

    state = {
        description: '',
        documentation: '',
        embargo_end_date: null,
        os: '',
        platforms: [],
        programming_languages: [],
        license: {
            name: 'GPL v3',
            url: 'https://opensource.org/licenses/gpl-license',
        },
        live: false
    };
    errors = {
        description: [],
        embargo_end_date: [],
        license: [],
        platforms: [],
        programming_languages: []
    };
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
    ]
    matchingPlatforms = [];
    isLoadingPlatforms = false;

    matchingProgrammingLanguages = [{ name: 'NetLogo' }, { name: 'Python'}];
    isLoadingProgrammingLanguages = false;

    @Watch('state.description')
    descriptionErrors(description) {
        validate(this, 'description', description);
    }

    @Watch('state.programming_languages')
    programmingLanguageErrors(programming_languages) {
        validate(this, 'programming_languages', programming_languages);
    }

    @Watch('state.platforms')
    platformErrors(platforms) {
        validate(this, 'platforms', platforms);
    }

    updateOs(value) {
        this.state.os = value.name
    }

    updatePlatforms(value) {
        this.state.platforms = value.name
    }

    updateProgrammingLanguages(value) {
        this.state.programming_languages = value.name;
    }

    save() {
        const { identifier, version_number } = this.identity;
        schema.validate(this.state, {abortEarly: false })
            .then(state =>
                api_base.put(`/codebases/${identifier}/releases/${version_number}/`, state)
                    .then(response => this.$store.dispatch('getCodebaseRelease', { identifier, version_number }),
                          _ => this.message = 'Submission failure'))
            .catch(ve => { 
                if (ve instanceof yup.ValidationError) {
                    ve.inner.forEach(ve_inner => {
                        this.errors[ve_inner.path] = [ve_inner.message];
                    })
                } else {
                    console.error(ve);
                }
            });
    }
}