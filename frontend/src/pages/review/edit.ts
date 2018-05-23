import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import {Invitations} from './invitations'
import {Feedback} from './feedback'
import {ReviewEditorAPI} from "api";
import {api} from "connection";
import {EventLog} from "./event_log";
import * as _ from 'lodash';

const reviewApi = new ReviewEditorAPI();

@Component({
    template: `<div class="container-fluid">
            <div class="row">
                <div class="col-sm-12 col-md-8">
                    <c-invitations :review_slug="review_slug" @pollEvents="retrieveEvents"></c-invitations>
                    <h2>Feedback</h2>
                    <c-feedback :review_slug="review_slug"></c-feedback>
                </div>
                <div class="col-sm-12 col-md-4">
                    <c-event-log :events="events" :errors="event_errors"></c-event-log>
                </div>
            </div>
    </div>`,
    components: {
        'c-event-log': EventLog,
        'c-invitations': Invitations,
        'c-feedback': Feedback,
    }
})
export class EditorReviewDetail extends Vue {
    @Prop()
    status_levels: Array<{ value: string, label: string }>;

    status: string = this.status_levels[0].value;

    @Prop()
    review_slug: string;

    @Prop()
    event_list_url: string;

    events: Array<object> = [];
    event_errors: Array<string> = [];

    async retrieveEvents() {
        try {
            const response = await api.axios.get(this.event_list_url);
            this.events = response.data;
            this.event_errors = [];
        } catch (e) {
            if (_.isArray(_.get(e, 'response.data'))) {
                this.event_errors = e.response.data;
            } else {
                this.event_errors = ['Error loading events']
            }
        }
    }

    created() {
        this.retrieveEvents();
    }
}