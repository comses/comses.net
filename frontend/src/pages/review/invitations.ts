import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import {ReviewEditorAPI} from "api/index";
import {ReviewerFinder} from "./reviewer_finder";
import {api} from "connection";
import {holder} from "pages/review/directives";
import * as _ from 'lodash'

const reviewApi = new ReviewEditorAPI();

@Component({
    // language=Vue
    template: `<div>
        <h2>Find and Invite a Reviewer</h2>
        <c-reviewer-finder v-model="candidate_reviewer" v-if="!candidate_reviewer"></c-reviewer-finder>
        <div class="container" v-else>
            <div class="row">
                <div class="col-2">
                    <img :src="candidate_reviewer.avatar">
                </div>
                <div class="col-10">
                    <h2>
                        {{ candidate_reviewer.name }}
                        <span class="pull-right">
                            <button class="btn btn-primary" @click="sendEmail">Invite</button>
                            <button class="btn btn-danger" @click="candidate_reviewer = null">Cancel</button>
                        </span>
                    </h2>
                    <div class="tag-list">
                        <div class="tag mx-1" v-for="tag in candidate_reviewer.tags">{{ tag.name }}</div>
                    </div>
                </div>
            </div>
        </div>
        <h2>Previous Invitees</h2>
        <div class="container-fluid" v-if="invitations.length > 0">
            <div class="row border-bottom py-2" v-for="invitation in invitations">
                <div class="col-xs-12 col-sm-2">
                    <img :src="invitation.candidate_reviewer.avatar_url" v-if="invitation.candidate_reviewer">
                    <span v-else>No image</span>
                </div>
                <div class="col-xs-12 col-sm-10">
                    <h3>
                        {{ displayTitle(invitation) }}
                        <span class="badge badge-info"></span>
                        <span class="float-md-right">
                            <button class="btn btn-outline-secondary">Resend Invite</button>
                        </span>
                    </h3>
                    <div class="tag-list">
                        <div class="tag mx-1" v-for="tag in candidateReviewerTags(invitation)">{{ tag.name }}</div>
                    </div>
                </div>
            </div>
        </div>
        <p v-else>No reviewers has been invited</p>
    </div>`,
    components: {
        'c-reviewer-finder': ReviewerFinder
    },
    directives: {
        holder
    }
})
export class Invitations extends Vue {
    candidate_reviewer = null;
    invitations: Array<any> = [];
    feedback: Array<any> = [];

    @Prop()
    review_uuid: string;

    get state() {
        return this.invitations;
    }

    candidateReviewerTags(invitation) {
        return invitation.candidate_reviewer ? invitation.candidate_reviewer.tags : [];
    }

    displayTitle(invitation) {
        if (!_.isNull(invitation.candidate_reviewer)) {
            return invitation.candidate_reviewer.name
        } else {
            return `External user (${invitation.candidate_email})`;
        }
    }

    async refresh() {
        const responseInvitations = await reviewApi.listInvitations(this.review_uuid);
        this.invitations = responseInvitations.data.results;
        const responseFeedback = await reviewApi.listFeedback(this.review_uuid);
        this.feedback = responseFeedback.data.results;
    }

    async created() {
        this.refresh();
    }

    async sendEmail() {
        const response = await api.axios.post(
            reviewApi.sendInvitationUrl({review_uuid: this.review_uuid}),
            this.candidate_reviewer);
        this.refresh();
    }
}