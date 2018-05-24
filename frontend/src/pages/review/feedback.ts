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
                    <a :href="feedback.editor_url">
                        <span class="text-success" v-if="feedback.recommendation">Recommended</span>
                        <span class="text-danger" v-else>Not Recommended</span>
                        by {{ feedback.reviewer_name }}
                    </a>
                </div>

                <div class="col-xs-12 col-sm-6">
                    <span class="badge badge-warning" v-if="!feedback.reviewer_submitted && !feedback.editor_submitted">Reviewer Has Not Submitted</span>
                    <span class="badge badge-secondary" v-else-if="feedback.reviewer_submitted && !feedback.editor_submitted">Reviewer Has Submitted</a>
                    <span class="badge badge-primary" v-else>Review Done</span>
                </div>
            </div>
        </div>
        <p v-else>No feedback has been received</p>
    </div>`
})
export class Feedback extends Vue {
    @Prop()
    review_slug: string;

    feedback_items: Array<any> = [];

    editorHasCompletedFeedback(feedback) {
        return !_.isEmpty(feedback.private_editor_notes) && !_.isEmpty(feedback.notes_to_author);
    }

    async created() {
        const response = await reviewApi.listFeedback(this.review_slug);
        this.feedback_items = response.data.results;
    }
}
