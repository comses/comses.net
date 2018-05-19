import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import {Invitations} from './invitations'
import {Feedback} from './feedback'
import {ReviewEditorAPI} from "api";

const reviewApi = new ReviewEditorAPI();

@Component({
    template: `<div>
        <c-invitations :review_slug="review_slug"></c-invitations>
        <h2>Feedback</h2>
        <c-feedback :review_slug="review_slug"></c-feedback>
    </div>`,
    components: {
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

    async saveStatus() {
        const response = await reviewApi.changeStatus({slug: this.review_slug}, this.status);
    }
}