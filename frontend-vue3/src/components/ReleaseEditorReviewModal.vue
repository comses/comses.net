<template>
  <span v-if="canRequest">
    <button type="button" :class="buttonClass" rel="nofollow" @click="reviewRequestModal.show()">
      Request Peer Review
    </button>
    <BootstrapModal
      id="review-request-modal"
      title="Request Peer Review"
      ref="reviewRequestModal"
      centered
    >
      <template #body>
        <p>Are you sure you want to request a peer review of this release?</p>
        <p class="text-muted mb-0">
          Read more about the CoMSES Net peer review process
          <a href="/reviews/" target="_blank">here</a>.
        </p>
        <FormAlert :validation-errors="[]" :server-errors="reviewRequestErrors" />
      </template>
      <template #footer>
        <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" @click="submitReviewRequest">
          Request Review
        </button>
      </template>
    </BootstrapModal>
  </span>

  <span v-else-if="canNotify">
    <button type="button" :class="buttonClass" rel="nofollow" @click="reviewNotifyModal.show()">
      Request Peer Review
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
        <button type="button" class="btn btn-danger" @click="submitReviewNotify">Send</button>
      </template>
    </BootstrapModal>
  </span>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { Modal } from "bootstrap";
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
  return !store.release.review_status;
});

const canNotify = computed(() => {
  return store.release.review_status === "awaiting_author_changes";
});

const reviewRequestModal = ref<typeof Modal>();
const reviewRequestErrors = ref<string[]>([]);
async function submitReviewRequest() {
  await post(store.release.urls.request_peer_review ?? "", null, {
    onSuccess(response) {
      store.release.review_status = response.data.review_status;
      store.release.urls = response.data.urls;
      reviewRequestModal.value?.hide();
    },
    onError(error) {
      if (error.response) {
        reviewRequestErrors.value = error.response.data as string[];
      }
    },
  });
}

const reviewNotifyModal = ref<typeof Modal>();
const reviewNotifyErrors = ref<string[]>([]);
async function submitReviewNotify() {
  await post(store.release.urls.notify_reviewers_of_changes ?? "", null, {
    onSuccess(response) {
      store.release.review_status = response.data.review_status;
      reviewNotifyModal.value.hide();
    },
    onError(error) {
      if (error.response) {
        reviewNotifyErrors.value = error.response.data as string[];
      }
    },
  });
}
</script>
