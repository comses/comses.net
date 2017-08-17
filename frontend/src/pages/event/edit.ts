import * as Vue from 'vue'
import  {CalendarEvent} from 'store/common'
import {api} from 'api/index'
import Markdown from 'components/forms/markdown'
import Tagger from 'components/tagger'
import Input from 'components/forms/input'
import Datepicker from 'components/forms/datepicker';
import MessageDisplay from 'components/message_display'
import * as _ from 'lodash'
import {Component, Prop} from "vue-property-decorator";
import * as yup from 'yup'

const schema = yup.object().shape({
    description: yup.string().required().meta({initial: ''}),
    summary: yup.string().meta({initial: ''}),
    title: yup.string().meta({initial: ''}),
    tags: yup.array().of(yup.object().shape({ name: yup.string().required()})).meta({initial: []}),
    location: yup.string().meta({initial: ''}),
    early_registration_deadline: yup.date().nullable().meta({initial: null}),
    submission_deadline: yup.date().nullable().meta({initial: null}),
    start_date: yup.date().required().meta({initial: null}),
    end_date: yup.date().meta({initial: null})
});

@Component({
    template: `<form>
        <c-input v-model="state.title" name="title" :errorMsgs="errors.title">
            <label class="form-control-label" slot="label">Title</label>
            <small class="form-text text-muted" slot="help">A short title describing the event</small>
        </c-input>
        <c-input v-model="state.location" name="location" :errorMsgs="errors.location">
            <label class="form-control-label" slot="label">Location</label>
            <small class="form-text text-muted" slot="help">The address of where the event takes place</small>
        </c-input>
        <div class="row">
            <div class="col-6">
                <c-datepicker v-model="state.start_date" name="start_date" :errorMsgs="errors.start_date">
                    <label class="form-control-label" slot="label">Start Date</label>
                    <small class="form-text text-muted" slot="help">The date the event begins at</small>
                </c-datepicker>
            </div>
            <div class="col-6">
                <c-datepicker v-model="state.end_date" name="end_date" :errorMsgs="errors.end_date" :clearButton="true">
                    <label class="form-control-label" slot="label">End Date</label>
                    <small class="form-text text-muted" slot="help">The date the event ends at</small>
                </c-datepicker>
            </div>
        </div>
        <div class="row">
            <div class="col-6 d-inline">
                <c-datepicker v-model="state.early_registration_deadline" name="early_registration_deadline"
                                :errorMsgs="errors.early_registration_deadline">
                    <label class="form-control-label" slot="label">Early Registration Deadline</label>
                    <small class="form-text text-muted" slot="help">The last day for early registration of the event
                        (inclusive)
                    </small>
                </c-datepicker>
            </div>
            <div class="col-6 d-inline">
                <c-datepicker v-model="state.submission_deadline" name="submission_deadline"
                                :errorMsgs="errors.submission_deadline"
                                :clearButton="true">
                    <label class="form-control-label" slot="label">Submission Deadline</label>
                    <small class="form-text text-muted" slot="help">The last day to register for the event (inclusive)
                    </small>
                </c-datepicker>
            </div>
        </div>
        <c-markdown v-model="state.description" name="description" :errorMsgs="errors.description"
                    @clear="clearField" validate="required" minHeight="20em">
            <label class="form-control-label" slot="label">Description</label>
            <small slot="help" class="form-text text-muted">Detailed information about the job</small>
        </c-markdown>
        <c-markdown v-model="state.summary" name="summary" :errorMsgs="errors.summary">
            <label slot="label">Summary</label>
            <div slot="help"><button class="btn btn-secondary btn-sm" type="button" @click="createSummaryFromDescription">
                    Summarize
                </button>
                <small class="form-text text-muted">A short summary of the job for display in search results.
                    This field can be created from the description by pressing the summarize button.
                </small>
            </div>
        </c-markdown>
        <c-tagger v-model="state.tags" name="tags" :errorMsgs="errors.tags">
        </c-tagger>
        <small class="form-text text-muted">A list of tags to associate with a job. Tags help people search for
            jobs.
        </small>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdate">Submit</button>
    </form>`,
    components: {
        'c-markdown': Markdown,
        'c-message-display': MessageDisplay,
        'c-datepicker': Datepicker,
        'c-tagger': Tagger,
        'c-input': Input
    },
    computed: {
        'tags': function () {
            const self: any = this;
            return self.data.tags.map(t => {
                return {name: t}
            });
        }
    }
})
class EditEvent extends Vue {
    // determine whether you are creating or updating based on wat route you are on
    // update -> grab the appropriate state from the store
    // create -> use the default store state

    @Prop
    id: number | null;

    state: CalendarEvent = {
        description: '',
        summary: '',
        title: '',
        tags: [],
        location: '',
        early_registration_deadline: '',
        submission_deadline: '',
        start_date: '',
        end_date: ''
    };

    clearField(field_name: string) {
        let self: any = this;
        self.errors.remove(field_name, 'server-side');
    }

    initializeForm() {
        if (this.id !== null) {
            this.retrieve(this.id);
        }
    }

    created() {
        this.initializeForm();
    }

    createSummaryFromDescription() {
        this.state.summary = _.truncate(this.state.description, {'length': 200, 'omission': '[...]'});
    }

    serverErrors(field_name: string) {
        let self: any = this;
        return self.errors.collect(field_name, 'server-side');
    }

    createOrUpdate() {
        if (this.state.id !== undefined) {
            this.update(this.state.id);
        } else {
            this.create();
        }
    }

    retrieve(id: number) {
        api.events.retrieve(id).then(state => this.state = state);
    }

    createMainServerError(err) {
        let self: any = this;
        self.errors.add('non_field_errors', err, 'server-side', 'server-side');
    }

    createServerErrors(err: any) {
        console.log({serverErrors: true, err});
        let self: any = this;
        if (err.hasOwnProperty('non_field_errors')) {
            this.createMainServerError((<any>err).non_field_errors);
            delete err.non_field_errors;
        }
        for (const field_name in err) {
            self.errors.add(field_name, err[field_name], 'server-side', 'server-side');
        }
    }

    create() {
        (this as any).errors.clear('server-side');
        api.events.create(this.state).then(drf_response => {
            (this as any).errors.clear('server-side');
            switch (drf_response.kind) {
                case 'state':
                    this.state = drf_response.payload;
                    break;
                case 'validation_error':
                    this.createServerErrors(drf_response.payload);
                    break;
            }
        });
    }

    update(id: number) {
        (this as any).errors.clear('server-side');
        api.events.update(id, this.state).then(drf_response => {
            switch (drf_response.kind) {
                case 'state':
                    this.state = drf_response.payload;
                    break;
                case 'validation_error':
                    this.createServerErrors(drf_response.payload);
                    break;
            }
        })
    }
}

export default EditEvent;