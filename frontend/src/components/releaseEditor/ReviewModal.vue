<template>
  <span v-if="canRequest">
    <button type="button" :class="buttonClass" rel="nofollow" @click="reviewRequestModal?.show()">
      Request Peer Review
    </button>
    <BootstrapModal
      id="review-request-modal"
      title="Request Peer Review"
      ref="reviewRequestModal"
      size="lg"
      centered
    >
      <template #body>
        <div class="alert alert-danger" role="alert">
          <p><b>Note</b></p>
          <p>
            Peer review may only occur on <strong>unpublished model releases</strong> so that you can
            continue to revise your code, data, and documentation based on reviewer guidance.
          </p>
          <p class="mb-0">
            If you have already published your model release or would like to do so before the review
            process is completed, <strong>a new draft release will be created</strong> for the review
            to take place on which will be an exact copy of the state of the model release at the time
            you request a review. On completion, the release can then be published to supersede
            unreviewed versions.
          </p>
        </div>
        <p>Are you sure you want to request a peer review of this release?</p>
        <p class="text-muted mb-0">
          Read more about the CoMSES Net peer review process
          <a href="/reviews/" target="_blank">here</a>.
        </p>
        <FormAlert :validation-errors="[]" :server-errors="reviewRequestErrors" />
      </template>
      <template #footer>
        <div v-if="!store.release.live" class="form-check me-auto">
          <input class="form-check-input" id="use-existing-draft" type="checkbox" v-model="useExistingDraft" />
          <label class="form-check-label" for="use-existing-draft">
            Use my current draft for peer review
          </label>
        <div id="emailHelp" class="form-text">You will be unable to publish it until the process is complete. A new release will be created if left unchecked.</div>
        </div>
        <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" @click="submitReviewRequest">
          <span v-if="isLoading"> <i class="fas fa-spinner fa-spin me-1"></i> Submitting Request... </span>
          <span v-else>Request Review</span>
        </button>
      </template>
    </BootstrapModal>
  </span>

  <span v-else-if="canNotify">
    <button type="button" :class="buttonClass" rel="nofollow" @click="reviewNotifyModal?.show()">
      Notify Reviewer of Changes
    </button>
    <BootstrapModal
      id="review-notify-modal"
      title="Notify Reviewers of Changes"
      ref="reviewNotifyModal"
      centered
    >
      <template #body>
        <p>Do you want to notify reviewers of changes to this release?</p>
        <FormAlert :validation-errors="[]" :server-errors="reviewNotifyErrors" />
      </template>
      <template #footer>
        <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" @click="submitReviewNotify">
          Send
        </button>
      </template>
    </BootstrapModal>
  </span>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useAxios } from "@/composables/api";
import { useReleaseEditorStore } from "@/stores/releaseEditor";

const props = defineProps<{
  buttonClass: string;
}>();

const store = useReleaseEditorStore();
const { post } = useAxios();

const canRequest = computed(() => {
  return !store.release.reviewStatus;
});

const canNotify = computed(() => {
  return store.release.reviewStatus === "awaiting_author_changes";
});

const useExistingDraft = ref(false);
const isLoading = ref(false);

const reviewRequestModal = ref<Modal>();
const reviewRequestErrors = ref<string[]>([]);

async function submitReviewRequest() {
  isLoading.value = true;
  let requestReviewUrl = store.release.urls.requestPeerReview ?? "";
  if (useExistingDraft.value) {
    requestReviewUrl += "?use_existing_draft";
  }
  await post(requestReviewUrl, null, {
    onSuccess(response) {
      store.release.reviewStatus = response.data.reviewStatus;
      store.release.urls = response.data.urls;
      window.location.href = response.data.reviewReleaseUrl;
    },
    onError(error) {
      if (error.response) {
        reviewRequestErrors.value = error.response.data as string[];
      }
    },
  });
  isLoading.value = false;
}

const reviewNotifyModal = ref<Modal>();
const reviewNotifyErrors = ref<string[]>([]);

async function submitReviewNotify() {
  await post(store.release.urls.notifyReviewersOfChanges ?? "", null, {
    onSuccess(response) {
      store.release.reviewStatus = response.data.reviewStatus;
      reviewNotifyModal.value?.hide();
    },
    onError(error) {
      if (error.response) {
        reviewNotifyErrors.value = error.response.data as string[];
      }
    },
  });
}
</script>
