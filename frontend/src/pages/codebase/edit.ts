import * as Vue from 'vue'
import {Component, Prop} from 'vue-property-decorator'
import {CodebaseAPI} from "api/index";
import Checkbox from 'components/forms/checkbox'
import Input from 'components/forms/input'
import Tagger from 'components/tagger'
import MarkdownEditor from 'components/forms/markdown'
import MessageDisplay from 'components/message_display'
import {createFormValidator} from "pages/form"
import * as yup from 'yup'
import * as _ from 'lodash'
import {HandlerWithRedirect, HandlerShowSuccessMessage} from "api/handler"
import Upload from "./release/upload";

export const schema = yup.object().shape({
    title: yup.string().required(),
    description: yup.string().required(),
    live: yup.bool(),
    is_replication: yup.bool(),
    tags: yup.array().of(yup.object().shape({name: yup.string().required()})).min(1).required(),
    repository_url: yup.string().url()
});

@Component(<any>{
    template: `<div>
        <p>
        Archiving the software that your research depends on will help others (including your future self!) build on and reuse your own hard work down the road. 
        Let's walk through the steps needed to generate a citable software archive that broadly follows recommended practices
        for <a href='https://www.force11.org/software-citation-principles'>software citation</a>.
        </p>
        <p>
        First, let's figure out what you'd like to call this thing.
        </p>
        <c-input v-model="title" name="title" :errorMsgs="errors.title" :required="config.title" label="Title"
            help="A short title describing the codebase">
        </c-input>
        <c-markdown v-model="description" :errorMsgs="errors.description" :required="config.description" 
            name="description" rows="3" label="Description">
        </c-markdown>
        <c-checkbox v-model="is_replication" :errorMsgs="errors.is_replication" name="replication" label="Replication"
            :required="config.is_replication"
            help="Is this model a replication of a prior computational model?">
        </c-checkbox>
        <c-tagger v-model="tags" name="tags" :errorMsgs="errors.tags" :required="config.tags" label="Tags">
        </c-tagger>
        <c-input v-model="repository_url" :errorMsgs="errors.repository_url" name="repository_url" label="Repository URL"
            help="URL to a version control source code repository (e.g., GitHub or BitBucket)"
            :required="config.repository_url">
        </c-input>
        <c-message-display :messages="statusMessages" @clear="statusMessages = []"></c-message-display>
        <!-- Media Uploads go here -->
        <button class="btn btn-primary" type="button" @click="save()">Save</button>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-input': Input,
        'c-markdown': MarkdownEditor,
        'c-message-display': MessageDisplay,
        'c-tagger': Tagger,
        'c-uploads': Upload
    }
})
export default class Description extends createFormValidator(schema) {
    private api = new CodebaseAPI();
    @Prop({default: null})
    _identifier: string;

    @Prop({default: true})
    redirect: boolean;

    detailPageUrl(state) {
        this.state.identifier = state.identifier;
        return this.api.detailUrl(this.state.identifier);
    }

    async initializeForm() {
        if (this._identifier) {
            const response = await this.api.retrieve(this._identifier);
            this.state = response.data;
        }
    }

    created() {
        this.initializeForm();
    }

    async createOrUpdate() {
        const handler = this.redirect ? HandlerWithRedirect : HandlerShowSuccessMessage;
        if (_.isNil(this.state.identifier)) {
            return this.api.create(new handler(this));
        } else {
            return this.api.update(this.state.identifier, new handler(this));
        }
    }

    async save() {
        await this.validate();
        return this.createOrUpdate();
    }
}
