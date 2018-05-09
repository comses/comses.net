import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import {Invitations} from './invitations'
import {Feedback} from './feedback'

@Component({
    template: `<div>
        <c-invitations :review_uuid="review_uuid"></c-invitations>
        <h2>Feedback</h2>
        <c-feedback :review_uuid="review_uuid"></c-feedback>
        <div class="form-group">
            <label for="status" class="form-control-label">Status</label>
            <select id="status" class="form-control">
                <option v-for="status_level in status_levels" value="status_level.value">
                    {{ status_level.label }}
                </option>
            </select>
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

    @Prop()
    review_uuid: string;
}