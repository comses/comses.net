<template>
  <div>
    <h2>Invite a Reviewer</h2>
    <div class="container-fluid" v-if="!candidateReviewer">
      <div class="row">
        <div class="col-12 px-0 mb-3">
          <UserSearch
            v-model="candidateReviewer"
            label="Search by name, email address, or username among existing CoMSES Net members"
            placeholder="Find a reviewer"
            :search-fn="findReviewers"
            :errors="serverErrors"
            show-avatar
            show-affiliation
            show-tags
            show-link
          />
        </div>
      </div>
    </div>
    <div class="container" v-else>
      <div class="row py-2">
        <div class="col-2 ps-0">
          <img
            v-if="candidateReviewer.avatarUrl"
            class="d-block img-thumbnail"
            :src="candidateReviewer.avatarUrl"
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
            {{ candidateReviewer.name }}
            <div class="btn-group float-end" role="group">
              <button class="btn btn-primary" @click="sendEmail" type="button">Invite</button>
              <button class="btn btn-danger" @click="candidateReviewer = null" type="button">
                Cancel
              </button>
            </div>
          </h2>
          <div class="tag-list">
            <div class="tag mx-1" v-for="tag in candidateReviewer.tags" :key="tag.name">
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
            v-if="inv.candidateReviewer.avatarUrl"
            class="d-block img-thumbnail"
            :src="inv.candidateReviewer.avatarUrl"
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
            {{ inv.candidateReviewer.name }}
            <span :class="`badge bg-${getStatusDisplay(inv).variant}`">{{
              getStatusDisplay(inv).label
            }}</span>
            <span class="float-md-end">
              <button class="btn btn-outline-secondary" @click="resendEmail(inv.slug)">
                Resend Invite
              </button>
            </span>
          </h3>
          <div class="tag-list">
            <div class="tag mx-1" v-for="tag in inv.candidateReviewer.tags" :key="tag.name">
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
import UserSearch from "@/components/UserSearch.vue";
import type { Reviewer } from "@/types";

const props = defineProps<{
  reviewId: string;
}>();

const emit = defineEmits(["pollEvents"]);

const { serverErrors, listInvitations, sendInvitation, resendInvitation, findReviewers } =
  useReviewEditorAPI();

const invitations = ref<any[]>([]);
const candidateReviewer = ref<Reviewer | null>(null);

onMounted(async () => {
  await retrieveInvitations();
});

async function retrieveInvitations() {
  const response = await listInvitations(props.reviewId);
  invitations.value = response.data.results;
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

function getStatusDisplay(invitation: any) {
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
