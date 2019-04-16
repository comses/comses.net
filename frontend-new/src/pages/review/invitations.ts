import {Component, Prop} from 'vue-property-decorator';
import Vue from 'vue';
import {ReviewEditorAPI} from '@/api/index';
import {ReviewerFinder} from './reviewer_finder';
import {api} from 'connection';
import {holder} from '@/pages/review/directives';
import * as _ from 'lodash';

const reviewApi = new ReviewEditorAPI();

@Component({
    // language=Vue
    template: `<div>
        <h2>Invite a Reviewer</h2>
        <p class="text-muted">
            Search by name, email address, or username among existing CoMSES Net members (<em>external reviewer invitation not implemented yet</em>)
        </p>
        <div class="container-fluid" v-if="!candidate_reviewer">
            <div class="row">
                <div class="col-12 px-0 mb-3">
                    <c-reviewer-finder v-model="candidate_reviewer"></c-reviewer-finder>
                </div>
            </div>
        </div>
        <div class="container" v-else>
            <div class="row">
                <div class="col-2">
                    <img :src="candidate_reviewer.avatar_url" class='img-fluid img-thumbnail'>
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
        <h2>Invited Reviewers</h2>
        <div class="container-fluid" v-if="invitations.length > 0">
            <div class="row border-bottom py-2" v-for="invitation in invitations">
                <div class="col-xs-12 col-sm-2">
                    <img :src="invitation.candidate_reviewer.avatar_url" v-if="invitation.candidate_reviewer" class='img-fluid img-thumbnail'>
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
        'c-reviewer-finder': ReviewerFinder,
    },
    directives: {
        holder,
    },
})
export class Invitations extends Vue {
    public candidate_reviewer = null;
    public candidate_email = '';
    public invitations: any[] = [];
    public feedback: any[] = [];

    @Prop()
    public review_slug: string;

    get state() {
        return this.invitations;
    }

    public candidateReviewerTags(invitation) {
        return invitation.candidate_reviewer ? invitation.candidate_reviewer.tags : [];
    }

    public displayTitle(invitation) {
        if (!_.isNull(invitation.candidate_reviewer)) {
            return invitation.candidate_reviewer.name;
        } else {
            return `External reviewer (${invitation.candidate_email})`;
        }
    }

    public displayInvitationStatus(invitation) {
        switch (invitation.accepted) {
            case true: {
                return 'Accepted';
            }
            case false: {
                return 'Declined';
            }
            default: {
                return 'Waiting for response';
            }
        }
    }

    public async refresh() {
        const responseInvitations = await reviewApi.listInvitations(this.review_slug);
        this.invitations = responseInvitations.data.results;
        const responseFeedback = await reviewApi.listFeedback(this.review_slug);
        this.feedback = responseFeedback.data.results;
    }

    public async created() {
        this.refresh();
    }

    public async sendEmail() {
        const response = await reviewApi.sendInvitation({review_uuid: this.review_slug}, this.candidate_reviewer);

        this.candidate_reviewer = null;
        this.refresh();
        this.$emit('pollEvents');
    }

    public async resendEmail(invitation_slug) {
        const response = await reviewApi.resendInvitation({slug: this.review_slug, invitation_slug});
        this.$emit('pollEvents');
    }
}
