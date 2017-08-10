import * as Vue from 'vue'
import { Component, Prop } from 'vue-property-decorator'
import { Codebase } from 'store/common'
import Checkbox from 'components/forms/checkbox.vue'
import Input from 'components/forms/input.vue'
import Tagger from 'components/tagger.vue'
import TextArea from 'components/forms/textarea.vue'
import { exposeComputed} from './store'
import * as yup from 'yup'

export const schema = yup.object();

@Component({
    template: `<div>
        <c-input v-model="codebaseTitle" name="title" :errorMsgs="codebaseTitleErrors" validate="required" label="Title"
            help="A short title describing the codebase">
        </c-input>
        <c-textarea v-model="codebaseDescription" :errorMsgs="codebaseDescriptionErrors" name="description" validate="required" rows="3">
            <label class="form-control-label" slot="label">Description</label>
        </c-textarea>
        <c-checkbox v-model="codebaseLive" name="live" :errorMsgs="codebaseLiveErrors" label="Published?"
            help="Published models are visible to everyone. Unpublished models are visible only to you">
        </c-checkbox>
        <c-checkbox v-model="codebaseIsReplication" :errorMsgs="codebaseIsReplicationErrors" name="replication" label="Is a replication?">
        </c-checkbox>
        <c-tagger v-model="codebaseTags" name="tags">
        </c-tagger>
        <c-input v-model="codebaseRepositoryUrl" :errorMsgs="codebaseRepositoryUrlErrors" name="repository_url" label="Repository URL"
            help="A link to the source repository (on GitHub, BitBucket etcetera). A source repository makes it easier for others collaberate with you on model development.">
        </c-input>
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

}