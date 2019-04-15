import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import {ReviewEditorAPI} from "@/api/index";
import * as _ from 'lodash';

const reviewApi = new ReviewEditorAPI();

@Component({
    template: `<div>
        <div class="container-fluid px-0" v-if="feedback_items.length > 0">
            <div class="row" v-for="feedback in feedback_items">
                <div class="col-xs-12 col-sm-6">
                    <a :href="feedback.editor_url">
                        {{ feedback.reviewer_name }} recommended: <mark>{{feedback.recommendation}}</mark>
                    </a>
                </div>
                <div class="col-xs-12 col-sm-6">
                    <span class='badge badge-info'>{{ feedback.review_status }} {{ feedback.date_created }}</span>
                </div>
            </div>
        </div>
        <p v-else>No reviewer feedback submitted yet</p>
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
