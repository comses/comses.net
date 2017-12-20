import * as Vue from 'vue'
import Markdown from 'components/forms/markdown'
import Tagger from 'components/tagger'
import Input from 'components/forms/input'
import MessageDisplay from 'components/message_display'
import DatePicker from 'components/forms/datepicker'
import {JobAPI} from 'api/index'
import * as _ from 'lodash'
import * as yup from 'yup'
import {Job} from 'store/common'
import {createFormValidator} from "pages/form"
import {Component, Prop} from "vue-property-decorator";
import {Mixin} from "util/vue-mixin";
import {HandlerWithRedirect} from "api/handler";

export const schema = yup.object().shape({
    title: yup.string().required(),
    description: yup.string().required(),
    application_deadline: yup.date().min(new Date(), "Please enter a valid date after today's date."),
    summary: yup.string().required(),
    tags: yup.array().of(yup.object().shape({name: yup.string().required()})).min(0),
    external_url: yup.string().url('Please enter a valid URL').nullable(),
});

@Component(<any>{
    template: `<form>
        <c-input v-model="title" name="title" :errorMsgs="errors.title" label="Title" :required="config.title"
            help="A short title describing the job">
        </c-input>
        <c-markdown v-model="description" name="description" :errorMsgs="errors.description" label="Description"
            help="Detailed information about the job" :required="config.description">
        </c-markdown>
        <c-markdown v-model="summary" name="summary" :errorMsgs="errors.summary" label="Summary"
            :required="config.summary">
            <div slot="help">
                <button class="btn btn-secondary btn-sm" type="button" @click="createSummaryFromDescription">Summarize
                </button>
                <small class="form-text text-muted">A short summary of the job for display in search results.
                    You can auto-create one from the description by clicking the Summarize button.
                </small>
            </div>
        </c-markdown>
        <c-input v-model="external_url" name="external_url" :errorMsgs="errors.external_url" :required="config.external_url"
            label="External Job URL" help="URL for this job on an external website">
        </c-input>
        <c-date-picker v-model="application_deadline" name="application_deadline" :clearButton="true" 
            :errorMsgs="errors.application_deadline" :required="false" label='Application deadline'>
        </c-date-picker>
        <c-tagger v-model="tags" name="tags" :errorsMsgs="errors.tags" :required="config.tags">
        </c-tagger>
        <small class="form-text text-muted">A list of tags to associate with a job. Tags help people search for jobs.
        </small>
        <c-message-display :messages="statusMessages">
        </c-message-display>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdateIfValid">Submit</button>
    </form>`,
    components: {
        'c-markdown': Markdown,
        'c-date-picker': DatePicker,
        'c-tagger': Tagger,
        'c-input': Input,
        'c-message-display': MessageDisplay,
    }
})
class EditJob extends createFormValidator(schema) {
    // determine whether you are creating or updating based on what route you are on
    // update -> grab the appropriate state from the store
    // create -> use the default store state
    private api = new JobAPI();

    @Prop()
    _id: number | null;

    detailPageUrl(state) {
        this.state.id = state.id;
        return this.api.detailUrl(this.state.id);
    }

    initializeForm() {
        if (this._id !== null) {
            return this.retrieve(this._id);
        }
    }

    created() {
        this.initializeForm();
    }

    createSummaryFromDescription() {
        this.state.summary = _.truncate(this.state.description, {'length': 200, 'omission': '[...]'});
    }

    async createOrUpdateIfValid() {
        await this.validate();
        this.createOrUpdate();
    }

    async createOrUpdate() {
        if (_.isNil(this.state.id)) {
            return this.api.create(new HandlerWithRedirect(this))
        } else {
            return this.api.update(this.state.id, new HandlerWithRedirect(this));
        }
    }

    retrieve(id: number) {
        return this.api.retrieve(id).then(r => {
            this.state = r.data;
            return r;
        });
    }
}

export default EditJob;
