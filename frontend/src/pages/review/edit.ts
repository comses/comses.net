import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import {Invitations} from './invitations'
import {Feedback} from './feedback'

@Component({
    template: `<div>
        <c-invitations :review_uuid="review_uuid"></c-invitations>
        <h2>Feedback</h2>
        <c-feedback :review_uuid="review_uuid"></c-feedback>
        <div>Status</div>
    </div>`,
    components: {
        'c-invitations': Invitations,
        'c-feedback': Feedback,
    }
})
export class EditorReviewDetail extends Vue {
    @Prop()
    review_uuid: string;
}