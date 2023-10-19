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
        <!-- FIXME: is there a way to deduplicate this + reminders.jinja -->
        <div class="alert alert-danger mb-4" role="alert">
          <p>
            <i class="fas fa-exclamation-triangle"></i> Peer reviews must be requested on
            <strong>unpublished model releases</strong> so that you can continue to revise your
            submission based on reviewer guidance.
          </p>
          <p class="mb-0">
            If you have already published your model
            <strong>a new draft release will be created</strong> as an exact copy of your most
            recent published release. If your model successfully passes peer review you can then
            choose to publish the reviewed release as the latest version.
          </p>
        </div>
        <p>
          Before submitting your peer review request, please ensure that your model conforms to the
          following <a href="/reviews/" target="_blank">review criteria</a>:
        </p>
        <ul class="mb-4">
          <li>
            <strong>Has "clean" source code</strong> that uses meaningful variable, method, and/or
            class names, is well-structured and consistently formatted for readability, has thorough
            comments that describe the semantics and intent of the code, and is in general
            <q cite="https://doi.org/10.1038/d41586-018-05004-4"
              >as simple as possible but no simpler</q
            >. The ideal goal we are striving for here is to make it as easy as possible for others
            (including your future self) to understand your code.
          </li>
          <li>
            <strong>Has detailed narrative documentation</strong> containing equations, flowcharts,
            or other diagrams in a structured format like the
            <a href="https://www.ufz.de/index.php?de=40429" target="_blank">ODD protocol</a> or
            equivalent. We
            <strong>do not recommend submitting a published journal article</strong> as your model's
            narrative documentation as they are often not detailed enough to allow others to fully
            reproduce your model and pose copyright issues for us to host.
          </li>
          <li>
            <strong>Is easily runnable</strong> without substantive changes to the downloaded
            package. Make sure to remove any absolute paths (e.g.,
            <code>/home/twubc/project/psyche/2023-01-14/data/hurn.nc</code> or
            <code>C:\Users\twubc\Downloads\data\ferns-and-wells.zip</code> or
            <code>/Users/twubc/data/ferns.nc</code>) from your source code and read the following
            note carefully for more details on how to reference any data files you upload to the
            Computational Model Library.
          </li>
        </ul>
        <div class="alert bg-gray" role="alert">
          <p><strong>Note on Uploaded Data</strong></p>
          <p class="mb-0">
            CoMSES Net stores uploaded data files in <code>&lt;project-root&gt;/data/</code> and
            code in <code>&lt;project-root&gt;/code/</code>. This means that your model will need to
            reference uploaded data files via a relative path like
            <code>"../data/my-input-data.csv"</code>. If you uploaded a zipfile with a nested
            directory structure you may need to go up several directories to get to the project root
            before descending back down into the data directory, depending on where your source code
            files exist within that nested directory structure. For example, a Python script in a
            <code>src/python/</code> directory would have to reference uploaded data files in
            <code>"../../../data/"</code>). This limitation can be sidestepped by including your
            data in your source code zipfile and referencing relative paths to your input data
            directly in your code and ignoring the CoMSES data upload slot.
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
