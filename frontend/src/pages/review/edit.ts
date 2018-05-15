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
        <div class="form-group">
            <label for="status" class="form-control-label">Status</label>
            <div class="input-group">
                <select id="status" class="form-control" v-model="status">
                    <option v-for="status_level in status_levels" :value="status_level.value" :selected="status_level.value === status">
                        {{ status_level.label }}
                    </option>
                </select>
                <div class="input-group-append">
                    <button type="button" class="btn btn-primary" @click="saveStatus">Save</button>
                </div>
            </div>
        </div>
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