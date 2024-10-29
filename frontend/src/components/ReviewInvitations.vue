<template>
  <div>
    <h2>Invite a Reviewer</h2>
    <div class="container-fluid" v-if="!candidateReviewer">
      <div class="row">
        <div class="col-12 px-0 mb-3">
          <ReviewerSearch
            v-model="candidateReviewer"
            label="Search by name, email address, or username among existing CoMSES Net members"
            placeholder="Find a reviewer"
          />
        </div>
      </div>
    </div>
    <div class="container" v-else>
      <div class="row py-2">
        <div class="col-2 ps-0">
          <img
            v-if="candidateReviewer.memberProfile.avatarUrl"
            class="d-block img-thumbnail"
            :src="candidateReviewer.memberProfile.avatarUrl"
            alt="Profile Image"
          />
          <img
            v-else
            class="d-block img-thumbnail"
            data-src="holder.js/100x100?text=No Picture Available"
            alt="No Picture Available"
          />
        </div>
        <div class="col-10 pe-0">
          <h2>
            {{ candidateReviewer.memberProfile.name }}
            <div class="btn-group float-end" role="group">
              <button class="btn btn-primary" @click="sendEmail" type="button">Invite</button>
              <button class="btn btn-danger" @click="candidateReviewer = null" type="button">
                Cancel
              </button>
            </div>
          </h2>
          <div class="tag-list">
            <div
              class="tag mx-1"
              v-for="tag in candidateReviewer.memberProfile.tags"
              :key="tag.name"
            >
              {{ tag.name }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <h2 class="mt-4">Invited Reviewers</h2>
    <div class="container-fluid" v-if="invitations && invitations.length > 0">
      <div class="row border-bottom py-2" v-for="inv in invitations" :key="inv.dateCreated">
        <div class="col-xs-12 col-sm-2 ps-0">
          <img
            v-if="inv.reviewer.memberProfile.avatarUrl"
            class="d-block img-thumbnail"
            :src="inv.reviewer.memberProfile.avatarUrl"
            alt="Profile Image"
          />
          <img
            v-else
            class="d-block img-thumbnail"
            data-src="holder.js/100x100?text=No Picture Available"
            alt="No Picture Available"
          />
        </div>
        <div class="col-xs-12 col-sm-10 pe-0">
          <h3>
            {{ inv.reviewer.memberProfile.name }}
            <span :class="`badge bg-${getStatusDisplay(inv).variant}`">{{
              getStatusDisplay(inv).label
            }}</span>
            <span class="float-md-end">
              <button
                v-if="!disabled"
                class="btn btn-outline-secondary"
                @click="resendEmail(inv.slug)"
              >
                Resend Invite
              </button>
            </span>
          </h3>
          <span v-if="!inv.accepted" class="badge bg-gray">Expires {{ inv.expirationDate }}</span>
          <div class="tag-list">
            <div class="tag mx-1" v-for="tag in inv.reviewer.memberProfile.tags" :key="tag.name">
              {{ tag.name }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <p v-else>No reviewers have been invited</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useReviewEditorAPI } from "@/composables/api";
import ReviewerSearch from "@/components/ReviewerSearch.vue";
import type { Reviewer, ReviewInvitation } from "@/types";

const props = defineProps<{
  reviewId: string;
  disabled: boolean;
}>();

const emit = defineEmits(["pollEvents"]);

const { listInvitations, sendInvitation, resendInvitation } = useReviewEditorAPI();

const invitations = ref<ReviewInvitation[]>([]);
const candidateReviewer = ref<Reviewer | null>(null);

onMounted(async () => {
  await retrieveInvitations();
});

async function retrieveInvitations() {
  const response = await listInvitations(props.reviewId);
  invitations.value = response.data.results;
  console.log(invitations.value);
}

async function sendEmail() {
  if (candidateReviewer.value) {
    await sendInvitation(props.reviewId, candidateReviewer.value);
    candidateReviewer.value = null;
    await retrieveInvitations();
    emit("pollEvents");
  }
}

async function resendEmail(invitationSlug: string) {
  await resendInvitation(props.reviewId, invitationSlug);
  emit("pollEvents");
}

function getStatusDisplay(invitation: ReviewInvitation) {
  let label = "";
  let variant = "";
  switch (invitation.accepted) {
    case true:
      label = "Accepted";
      variant = "success";
      break;
    case false:
      label = "Declined";
      variant = "danger";
      break;
    default:
      label = "Waiting for response";
      variant = "info";
      break;
  }
  return {
    label,
    variant,
  };
}
</script>
