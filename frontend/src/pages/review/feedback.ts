import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import {ReviewEditorAPI} from "api/index";
import * as _ from 'lodash';

const reviewApi = new ReviewEditorAPI();

@Component({
    template: `<div>
        <div class="container-fluid px-0" v-if="feedback_items.length > 0">
            <div class="row" v-for="feedback in feedback_items">
                <div class="col-xs-12 col-sm-6">
                    <span class="text-success" v-if="feedback.recommendation">Recommended</span>
                    <span class="text-danger" v-else>Not Recommended</span>
                    by {{ feedback.reviewer_name }}
                </div>
                <div class="col-xs-12 col-sm-6">
                    <span class="badge badge-primary" v-if="editorHasCompletedFeedback(feedback)">Review Complete</span>
                    <a class="badge badge-warning" v-else>Review Needed</a>
                </div>
            </div>
        </div>
        <p v-else>No feedback has been received</p>
    </div>`
})
export class Feedback extends Vue {
    @Prop()
    review_uuid: string;

    feedback_items: Array<any> = [];

    editorHasCompletedFeedback(feedback) {
        return !_.isEmpty(feedback.private_editor_notes) && !_.isEmpty(feedback.notes_to_author);
    }

    async created() {
        const response = await reviewApi.listFeedback(this.review_uuid);
        this.feedback_items = response.data.results;
    }
}