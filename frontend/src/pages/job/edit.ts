import * as Vue from 'vue'
import Markdown from 'components/forms/markdown'
import Tagger from 'components/tagger'
import Input from 'components/forms/input'
import MessageDisplay from 'components/message_display'
import {jobAPI} from 'api/index'
import * as _ from 'lodash'
import * as yup from 'yup'
import {Job} from 'store/common'
import {createFormValidator} from "pages/form"
import {Component, Prop} from "vue-property-decorator";

export const schema = yup.object().shape({
    title: yup.string().required(),
    description: yup.string().required(),
    summary: yup.string().required(),
    tags: yup.array().of(yup.object().shape({name: yup.string().required()})).min(1)
});

@Component(<any>{
    template: `<form>
        <c-message-display :messages="[]" :classNames="['alert', 'alert-danger']">
        </c-message-display>
        <c-input v-model="title" name="title" :errorMsgs="errors.title">
            <label class="form-control-label" slot="label">Title</label>
            <small class="form-text text-muted" slot="help">A short title describing the job</small>
        </c-input>
        <c-markdown v-model="description" name="description" :errorMsgs="errors.description">
            <label class="form-control-label" slot="label">Description</label>
            <small slot="help" class="form-text text-muted">Detailed information about the job</small>
        </c-markdown>
        <c-markdown v-model="summary" name="summary" :errorMsgs="errors.summary">
            <label slot="label">Summary</label>
            <div slot="help">
                <button class="btn btn-secondary btn-sm" type="button" @click="createSummaryFromDescription">Summarize
                </button>
                <small class="form-text text-muted">A short summary of the job for display in search results.
                    This field can be created from the description by pressing the summarize button.
                </small>
            </div>
        </c-markdown>
        <c-tagger v-model="tags" name="tags" :errorsMsgs="errors.tags">
        </c-tagger>
        <small class="form-text text-muted">A list of tags to associate with a job. Tags help people search for jobs.
        </small>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdate">Submit</button>
    </form>`,
    components: {
        'c-markdown': Markdown,
        'c-tagger': Tagger,
        'c-input': Input,
        'c-message-display': MessageDisplay,
    },
    mixins: [
        createFormValidator(schema)
    ]
})
class EditJob extends Vue {
    // determine whether you are creating or updating based on what route you are on
    // update -> grab the appropriate state from the store
    // create -> use the default store state

    @Prop()
    id: number | null;

    initializeForm() {
        if (this.id !== null) {
            return this.retrieve(this.id);
        }
    }

    created() {
        this.initializeForm();
    }

    createSummaryFromDescription() {
        (<any>this).state.summary = _.truncate((<any>this).state.description, {'length': 200, 'omission': '[...]'});
    }

    createOrUpdate() {
        const self: any = this;
        if (this.id === null) {
            return jobAPI.create(self.state)
        } else {
            return jobAPI.update(self.state);
        }
    }

    createOrUpdateIfValid() {
        const self: any = this;
        self.validate().then(() => {
            this.createOrUpdate()
        });
    }

    retrieve(id: number) {
        return jobAPI.retrieve(id).then(r => {
            (<any>this).state = r.data;
            return r;
        });
    }
}

export default EditJob;