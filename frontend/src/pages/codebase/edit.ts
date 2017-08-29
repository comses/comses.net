import * as Vue from 'vue'
import { Component, Prop } from 'vue-property-decorator'
import { codebaseAPI } from "api/index";
import Checkbox from 'components/forms/checkbox'
import Input from 'components/forms/input'
import Tagger from 'components/tagger'
import TextArea from 'components/forms/textarea'
import { createFormValidator } from "pages/form";
import * as yup from 'yup'

export const schema = yup.object().shape({
    title: yup.string().required(),
    description: yup.string().required(),
    live: yup.bool(),
    is_replication: yup.bool(),
    tags: yup.array().of(yup.object().shape({ name: yup.string().required()})).min(1),
    repository_url: yup.string().url()
});

@Component(<any>{
    template: `<div>
        <c-input v-model="state.title" name="title" :errorMsgs="errors.title" label="Title"
            help="A short title describing the codebase">
        </c-input>
        <c-textarea v-model="state.description" :errorMsgs="errors.description" name="description" rows="3">
            <label class="form-control-label" slot="label">Description</label>
        </c-textarea>
        <c-checkbox v-model="state.live" name="live" :errorMsgs="errors.live" label="Published?"
            help="Published models are visible to everyone. Unpublished models are visible only to you">
        </c-checkbox>
        <c-checkbox v-model="state.is_replication" :errorMsgs="errors.is_replication" name="replication" label="Is a replication?">
        </c-checkbox>
        <c-tagger v-model="state.tags" name="tags" :errorMsgs="errors.tags" label="Tags">
        </c-tagger>
        <c-input v-model="state.repository_url" :errorMsgs="errors.repository_url" name="repository_url" label="Repository URL"
            help="A link to the source repository (on GitHub, BitBucket etcetera). A source repository makes it easier for others collaberate with you on model development.">
        </c-input>
        <button class="btn btn-primary" type="button" @click="save()">Save</button>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-input': Input,
        'c-textarea': TextArea,
        'c-tagger': Tagger,
    },
    mixins: [
        createFormValidator(schema, {
            errorAttributeName: 'errors',
            stateAttributeName: 'state'
        }, {
            clearErrorsMethodName: 'clear',
            validationMethodName: 'validate'
        })
    ]
})
export default class Description extends Vue {
    @Prop()
    identifier: string;

    async created() {
        const response = await codebaseAPI.retrieve(this.identifier);
        (<any>this).state = response.data;
    }

    async save() {
        let self: any = this;
        await self.validate();
        return codebaseAPI.update(self.state);
    }
}