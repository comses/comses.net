import * as Vue from 'vue'
import { Component, Prop} from 'vue-property-decorator'
import Datepicker from 'components/forms/datepicker.vue'
import Markdown from 'components/forms/markdown.vue'
import TextArea from 'components/forms/textarea.vue'
import Input from 'components/forms/input.vue'
import Multiselect from 'vue-multiselect'
import { exposeComputed } from './store'

@Component(<any>{
    template: `<div>
        <c-textarea v-model="description" name="description" rows="3">
            <label class="form-control-label" slot="label">Description</label>
        </c-textarea>
        <c-datepicker v-model="embargoEndDate" name="embargoEndDate">
            <label class="form-control-label" slot="label">Embargo End Date</label>
            <small class="form-text text-muted" slot="help">The date your release is automatically published</small>
        </c-datepicker>
        <div class="form-group">
            <label class="form-control-label">Operating System</label>
            <multiselect 
                :value="os"
                @input="updateOs"
                name="os" 
                :options="osOptions" 
                placeholder="Pick the OS the model runs on"
                label="display"
                track-by="name">
            </multiselect>
        </div>
        <div class="form-group">
            <label class="form-control-label">Platforms</label>
            <multiselect
                :value="platforms"
                @input="updatePlatforms"
                label="platforms"
                track-by="name"
                placeholder="Type to find platforms"
                :options="matchingPlatforms"
                :multiple="true"
                :loading="isLoadingPlatforms"
                :searchable="true"
                :internal-search="false"
                :clear-on-select="false"
                :close-on-select="false"
                :options-limit="50"
                :limit="20"
                @search-change="fetchMatchingPlatforms">
            </multiselect>
        </div>
        <div class="form-group">
            <label class="form-control-label">Programming Languages</label>
            <multiselect
                :value="programmingLanguages"
                @input="updateProgrammingLanguages"
                label="name"
                track-by="name"
                placeholder="Type to find programming languages"
                :options="matchingProgrammingLanguages"
                :multiple="true"
                :loading="isLoadingProgrammingLanguages"
                :searchable="true"
                :internal-search="false"
                :clear-on-select="false"
                :close-on-select="false"
                :options-limit="50"
                :limit="6"
                @search-change="fetchMatchingProgrammingLanguages">
            </multiselect>
        </div>
    </div>`,
    components: {
        'c-datepicker': Datepicker,
        'c-input': Input,
        'c-markdown': Markdown,
        'c-textarea': TextArea,
        Multiselect
    },
    computed: exposeComputed(['description', 'documentation', 'embargo_end_date', 'os', 'platforms', 'programming_languages'])
})
export default class Description extends Vue {
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

    updateOs(value) {
        (<any>this).os = value.name
    }

    updatePlatforms() {

    }

    fetchMatchingPlatforms() {

    }

    updateProgrammingLanguages() {

    }

    fetchMatchingProgrammingLanguages() {

    }
}