import * as Vue from 'vue'
import {CalendarEvent} from 'store/common'
import {eventAPI} from 'api'
import Markdown from 'components/forms/markdown'
import Tagger from 'components/tagger'
import Input from 'components/forms/input'
import Datepicker from 'components/forms/datepicker';
import MessageDisplay from 'components/message_display'
import * as _ from 'lodash'
import {Component, Prop} from "vue-property-decorator";
import * as yup from 'yup'
import {createFormValidator, reachRelated} from "pages/form"
import {Mixin} from 'util/vue-mixin';
import {HandlerWithRedirect} from "api/handler";

function dateAfterConstraint(before_name: string, after_name: string) {
    return (before_date, schema) => {
        if (_.isNil(before_date) || _.isNaN(before_date.getDate())) {
            return schema;
        } else {
            return schema.min(before_date, `${_.capitalize(after_name)} must be after ${before_name}`);
        }
    }
}

export const schema = yup.object().shape({
    description: yup.string().required(),
    summary: yup.string(),
    title: yup.string().required(),
    tags: yup.array().of(yup.object().shape({name: yup.string().required()})),
    location: yup.string().required(),
    early_registration_deadline: yup.date().nullable(),
    submission_deadline: yup.date().nullable()
        .when('early_registration_deadline', dateAfterConstraint('early registration deadline', 'submission deadline')),
    start_date: yup.date().required()
        .when('submission_deadline', dateAfterConstraint('submission deadline', 'start date')),
    end_date: yup.date().nullable()
        .when('start_date', dateAfterConstraint('start date', 'end date'))
});

@Component(<any>{
    template: `<form>
        <c-input v-model="title" name="title" :errorMsgs="errors.title">
            <label class="form-control-label" slot="label">Title</label>
            <small class="form-text text-muted" slot="help">A short title describing the event</small>
        </c-input>
        <c-input v-model="location" name="location" :errorMsgs="errors.location">
            <label class="form-control-label" slot="label">Location</label>
            <small class="form-text text-muted" slot="help">The address of where the event takes place</small>
        </c-input>
        <div class="row">
            <div class="col-6">
                <c-datepicker v-model="start_date" name="start_date" :errorMsgs="errors.start_date">
                    <label class="form-control-label" slot="label">Start Date</label>
                    <small class="form-text text-muted" slot="help">The date the event begins at</small>
                </c-datepicker>
            </div>
            <div class="col-6">
                <c-datepicker v-model="end_date" name="end_date" :errorMsgs="errors.end_date" :clearButton="true">
                    <label class="form-control-label" slot="label">End Date</label>
                    <small class="form-text text-muted" slot="help">The date the event ends at</small>
                </c-datepicker>
            </div>
        </div>
        <div class="row">
            <div class="col-6 d-inline">
                <c-datepicker v-model="early_registration_deadline" name="early_registration_deadline"
                                :errorMsgs="errors.early_registration_deadline" :clearButton="true">
                    <label class="form-control-label" slot="label">Early Registration Deadline</label>
                    <small class="form-text text-muted" slot="help">The last day for early registration of the event
                        (inclusive)
                    </small>
                </c-datepicker>
            </div>
            <div class="col-6 d-inline">
                <c-datepicker v-model="submission_deadline" name="submission_deadline"
                    :errorMsgs="errors.submission_deadline" :clearButton="true">
                    <label class="form-control-label" slot="label">Submission Deadline</label>
                    <small class="form-text text-muted" slot="help">The last day to register for the event (inclusive)
                    </small>
                </c-datepicker>
            </div>
        </div>
        <c-markdown v-model="description" name="description" :errorMsgs="errors.description"
                    minHeight="20em" label="Description" help="Detailed information about the event">
        </c-markdown>
        <c-markdown v-model="summary" name="summary" :errorMsgs="errors.summary">
            <label slot="label">Summary</label>
            <div slot="help"><button class="btn btn-secondary btn-sm" type="button" @click="createSummaryFromDescription">
                    Summarize
                </button>
                <small class="form-text text-muted">A short summary of the job for display in search results.
                    This field can be created from the description by pressing the summarize button.
                </small>
            </div>
        </c-markdown>
        <c-tagger v-model="tags" name="tags" :errorMsgs="errors.tags" label="Tags">
        </c-tagger>
        <small class="form-text text-muted">A list of tags to associate with a job. Tags help people search for
            jobs.
        </small>
        <c-message-display :messages="statusMessages"></c-message-display>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdateIfValid">Submit</button>
    </form>`,
    components: {
        'c-markdown': Markdown,
        'c-message-display': MessageDisplay,
        'c-datepicker': Datepicker,
        'c-tagger': Tagger,
        'c-input': Input
    },
})
class EditEvent extends createFormValidator(schema) {
    // determine whether you are creating or updating based on wat route you are on
    // update -> grab the appropriate state from the store
    // create -> use the default store state

    @Prop
    _id: number | null;

    detailPageUrl(state) {
        this.state.id = state.id;
        return eventAPI.detailUrl(this.state.id);
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
        (<any>this).state.summary = _.truncate(this.state.description, {'length': 200, 'omission': '[...]'});
    }

    async createOrUpdateIfValid() {
        await this.validate();
        this.createOrUpdate();
    }

    createOrUpdate() {
        if (_.isNil(this.state.id)) {
            return eventAPI.create(new HandlerWithRedirect(this));
        } else {
            return eventAPI.update(this.state.id, new HandlerWithRedirect(this));
        }
    }

    retrieve(id: number) {
        return eventAPI.retrieve(id).then(r => this.state = r.data);
    }
}

export default EditEvent;