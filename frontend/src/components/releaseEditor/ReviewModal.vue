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
      scrollable
      centered
    >
      <template #body>
        <div class="alert alert-danger mb-4" role="alert">
          <p>
            <i class="fas fa-exclamation-triangle"></i> Peer reviews may only occur on
            <strong>unpublished model releases</strong> so that you can continue to revise your
            submission based on reviewer guidance.
          </p>
          <p class="mb-0">
            If you have already published your model
            <strong>a new draft release will be created</strong> as an exact copy. On completion,
            the release can then be published to supersede unreviewed versions.
          </p>
        </div>
        <p>
          Before submitting your peer review request, please ensure that your model conforms to the
          following <a href="/reviews/" target="_blank">review criteria</a>:
        </p>
        <ul class="mb-4">
          <li>
            <strong>Clean source code</strong> that is well-commented, uses meaningful variable
            names, consistently formatted, etc.
          </li>
          <li>
            <strong>Detailed narrative documentation</strong> containing equations, flowcharts, or
            other diagrams in a structured format like the
            <a href="https://www.ufz.de/index.php?de=40429" target="_blank">ODD protocol</a> or
            equivalent. Published journal articles generally are not considered sufficient narrative
            documentation and pose copyright issues for us to host.
          </li>
          <li>
            <strong>Runnable</strong> without any changes to the downloaded package. Take care to
            remove absolute paths from your source code and see the following note for referencing
            data files.
          </li>
        </ul>
        <div class="alert bg-gray" role="alert">
          <p><strong>Note on Uploaded Data</strong></p>
          <p class="mb-0">
            <small
              >CoMSES Net stores uploaded data files in <code>&lt;project-root&gt;/data/</code> and
              code in <code>&lt;project-root&gt;/code/</code>. This means that references to your
              uploaded data files within your model will typically be via a relative path like
              <code>"../data/my-input-data.csv"</code>. If you uploaded a zipfile with a nested
              directory structure you may need to go up several directories to get to the project
              root before descending back down into the data directory, depending on where your
              source code files exist within that nested directory structure (e.g., a Python script
              in a <code>src/python/</code> directory would have to reference uploaded data files in
              <code>"../../../data/"</code>). This can be mitigated by including your data in your
              source code zipfile and referencing relative paths to your input data directly in your
              code and ignoring the CoMSES data upload slot.
            </small>
          </p>
        </div>
        <FormAlert :validation-errors="[]" :server-errors="reviewRequestErrors" />
      </template>
      <template #footer>
        <div v-if="!store.release.live" class="me-auto form-text">
          * You will be unable to publish this release until the process is complete.
        </div>
        <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" @click="submitReviewRequest">
          <span v-if="isLoading">
            <i class="fas fa-spinner fa-spin me-1"></i> Submitting Request...
          </span>
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
        <button type="button" class="btn btn-danger" @click="submitReviewNotify">Send</button>
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

const isLoading = ref(false);

const reviewRequestModal = ref<Modal>();
const reviewRequestErrors = ref<string[]>([]);

async function submitReviewRequest() {
  isLoading.value = true;
  let requestReviewUrl = store.release.urls.requestPeerReview ?? "";
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
