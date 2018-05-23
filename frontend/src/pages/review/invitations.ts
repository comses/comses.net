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
        <p class="text-muted">
            Find an internal or external reviewer for the model. Add an external reviewer using an email address or
            an internal reviewer.
        </p>
        <div class="container-fluid" v-if="!candidate_reviewer">
            <div class="row">
                <div class="col-xs-12 col-sm-10 px-0">
                    <div class="form-group mb-0" v-if="candidate_is_external">
                        <input type="email" class="form-control" placeholder="Enter email" v-model="candidate_email">
                    </div>
                    <c-reviewer-finder v-model="candidate_reviewer" v-else></c-reviewer-finder>
                </div>
                <div class="col-xs-12 col-sm-2 px-0">
                    <div class="btn-group w-100 h-100" v-if="candidate_is_external">
                        <button class="btn btn-block btn-outline-secondary" @click="sendEmail">Invite</button>
                        <button class="btn btn-block btn-outline-info mt-0 h-100" @click="candidate_is_external = false">Find Reviewer</button>
                    </div>
                    <button class="btn btn-outline-info h-100 w-100" @click="candidate_is_external = true" v-else>Email Only</button>
                </div>
            </div>
        </div>
        <div class="container" v-else>
            <div class="row">
                <div class="col-2">
                    <img :src="candidate_reviewer.avatar_url">
                </div>
                <div class="col-10">
                    <h2>
                        {{ candidate_reviewer.name }}
                        <span class="pull-right">
                            <button class="btn btn-primary" @click="sendEmail" type="button">Invite</button>
                            <button class="btn btn-danger" @click="candidate_reviewer = null" type="button">Cancel</button>
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
                        <span class="badge badge-info">{{ displayInvitationStatus(invitation) }}</span>
                        <span class="float-md-right">
                            <button class="btn btn-outline-secondary" @click="resendEmail(invitation.slug)">Resend Invite</button>
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
    candidate_email = '';
    invitations: Array<any> = [];
    feedback: Array<any> = [];
    candidate_is_external = false;

    @Prop()
    review_slug: string;

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
            return `External reviewer (${invitation.candidate_email})`;
        }
    }

    displayInvitationStatus(invitation) {
        switch (invitation.accepted) {
            case true: {
                return 'Accepted'
            }
            case false: {
                return 'Rejected'
            }
            default: {
                return 'Waiting for response'
            }
        }
    }

    async refresh() {
        const responseInvitations = await reviewApi.listInvitations(this.review_slug);
        this.invitations = responseInvitations.data.results;
        const responseFeedback = await reviewApi.listFeedback(this.review_slug);
        this.feedback = responseFeedback.data.results;
    }

    async created() {
        this.refresh();
    }

    async sendEmail() {
        if (this.candidate_is_external) {
            const response = await reviewApi.sendInvitation({review_uuid: this.review_slug}, {email: this.candidate_email});
        } else {
            const response = await reviewApi.sendInvitation({review_uuid: this.review_slug}, this.candidate_reviewer);
        }

        this.candidate_reviewer = null;
        this.candidate_email = '';
        this.refresh();
        this.$emit('pollEvents');
    }

    async resendEmail(invitation_slug) {
        const response = await reviewApi.resendInvitation({slug: this.review_slug, invitation_slug});
        this.$emit('pollEvents');
    }
}