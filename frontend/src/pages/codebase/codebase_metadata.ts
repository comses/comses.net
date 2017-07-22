import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'
import { Component, Prop } from 'vue-property-decorator'
import { Codebase } from 'store/common'
import Checkbox from 'components/forms/checkbox.vue'
import Input from 'components/forms/input.vue'
import Tagger from 'components/tagger.vue'
import TextArea from 'components/forms/textarea.vue'
import { exposeComputed} from './store'

Vue.use(VeeValidate)

@Component({
    template: `<div>
        <c-input v-model="codebaseTitle" name="title" validate="required">
            <label class="form-control-label" slot="label">Title</label>
            <small class="form-text text-muted" slot="help">A short title describing the codebase</small>
        </c-input>
        <c-textarea v-model="codebaseDescription" name="description" validate="required" rows="3">
            <label class="form-control-label" slot="label">Description</label>
        </c-textarea>
        <c-checkbox v-model="codebaseLive" name="live" label="Published?">
            <small class="form-text text-muted" slot="help">Published models are visible to everyone. Unpublished models are visible only to you</small>
        </c-checkbox>
        <c-checkbox v-model="codebaseIsReplication" name="replication" label="Is a replication?">
        </c-checkbox>
        <c-tagger v-model="codebaseTags" name="tags">
        </c-tagger>
        <c-input v-model="codebaseRepositoryUrl" name="repository_url" type="url">
            <label class="form-control-label" slot="label">Repository URL</label>
            <small class="form-text text-muted" slot="help">A link to the source repository (on GitHub, BitBucket etcetera). A source repository makes it easier for others collaberate with you on model development.
            </small>
        </c-input>
        <button class="btn btn-primary" type="button" @click="validate">Validate</button>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-input': Input,
        'c-textarea': TextArea,
        'c-tagger': Tagger,
    },
    computed: <any>exposeComputed(
        ['codebase.title', 'codebase.description', 'codebase.live', 'codebase.is_replication', 'codebase.tags', 'codebase.repository_url'])
})
export default class Description extends Vue {
    validate() {
        this.$validator.validateAll().then(result => {
            if (result) {
                console.log('success');
            } else {
                console.log('fail');
            }
        })
    }
}