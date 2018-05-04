import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import {ReviewEditorAPI} from "api/index";
import {ReviewerFinder} from "./reviewer_finder";
import {baseHandleOtherError, CreateOrUpdateHandler, FormComponent} from "handler";
import {AxiosResponse} from "axios";
import {api} from "connection";

const reviewApi = new ReviewEditorAPI();

@Component({
    // language=Vue
    template: `<div>
        <h2>Find and Invite a Reviewer</h2>
        <c-reviewer-finder v-model="candidate_reviewer" v-if="!candidate_reviewer"></c-reviewer-finder>
        <div class="container" v-if="candidate_reviewer">
            <div class="row">
                <div class="col-2">
                    <img :src="candidate_reviewer.avatar">
                </div>
                <div class="col-10">
                    <h2>
                        {{ candidate_reviewer.full_name }}
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
            <div class="row" v-for="invitation in invitations">
                <div class="col-sm-12 col-md-4">{{ invitation.name }}</div>
                <div class="col-sm-6 col-md-4">{{ invitation.date_invited }}</div>
                <div class="col-sm-6 col-md-4">{{ invitation.n_incomplete_reviews }}</div>
            </div>
        </div>
        <p v-else>No reviewers has been invited</p>
    </div>`,
    components: {
        'c-reviewer-finder': ReviewerFinder
    }
})
export class Invitations extends Vue {
    candidate_reviewer = null;
    invitations: Array<{name: string, date_invited: string, n_incomplete_reviews: number}> = [];

    @Prop()
    review_uuid: string;

    get state() {
        return this.invitations;
    }

    async created() {
        const response = await reviewApi.listFeedback(this.review_uuid);
        this.invitations = response.data.results;
    }

    async sendEmail() {
        const response = await api.axios.post(
            reviewApi.sendInvitationUrl({review_uuid: this.review_uuid}),
            this.candidate_reviewer);
    }
}