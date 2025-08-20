<template>
  <button v-if="store.release.live" type="button" :class="`${buttonClass} disabled`">
    <i class="fas fa-share-alt"></i> Published
  </button>
  <button v-else :class="buttonClass" rel="nofollow" @click="publishModal?.show()">
    <i class="fas fa-share-alt"></i> Publish
  </button>
  <BootstrapModal id="publish-modal" title="Publish Release" ref="publishModal" size="lg" centered>
    <template #body>
      <p>
        <b>Please read carefully!</b> <b>Publishing</b> a model release makes it public so anyone may view and download
        it. Once a model release is published, all files associated with the release will be <b>frozen</b> and you will
        not be able to add or remove files to the release. You <b>can still edit your model release's metadata</b> after
        publication. If you would like a DOI for your model to support software citation best practices (highly
        recommended!), <a href="/reviews/">request a peer review</a> of your model before publishing it so you can
        address any reviewer concerns that may include changes to the files associated with your release.
      </p>
      <p>
        You must assign a <em>semantic version number</em> to this release when you publish it. We recommend the
        <a target="_blank" href="https://semver.org">semantic versioning</a> standard which splits a version number into
        three parts: major, minor and patch. For example, version 2.7.18 has major version 2, minor version 7, and patch
        version 18. Increase the <i>major</i> version (leftmost number) if this new release is backwards incompatible
        with the previous release. Increase the <i>minor</i> version (middle number) if this release introduced new
        features but is still backwards compatible. Increase the <i>patch</i> version (rightmost number) if this release
        only contains bug fixes and is still backwards compatible (without the bugs).
      </p>
      <p>
        We also recommend that you include a screenshot or other representative image of your model to improve its
        visibility and discoverability; these images are prominently displayed on our front page's featured model
        gallery, in the model library, and search results.
      </p>
      <form id="publish-form" class="mb-3" @submit="handleSubmit">
        <TextField name="versionNumber" label="Version Number" help="" required>
          <template #help>
            <small class="form-text text-muted" aria-describedby="versionNumber">
              <a target="_blank" href="https://semver.org/">more info on semantic versioning</a>
            </small>
            <small class="form-text text-muted"> </small>
          </template>
        </TextField>
        <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
      </form>
      <p class="mb-0">Publishing a release cannot be undone. Proceed?</p>
    </template>
    <template #footer>
      <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
      <button type="submit" data-cy="publish" class="btn btn-danger" form="publish-form">
        Publish
      </button>
    </template>
  </BootstrapModal>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { onMounted, ref, watch } from "vue";
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";
import TextField from "@/components/form/TextField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useForm } from "@/composables/form";
import { useReleaseEditorAPI } from "@/composables/api";
import { useReleaseEditorStore } from "@/stores/releaseEditor";

const props = defineProps<{
  buttonClass: string;
  show: boolean;
}>();

const store = useReleaseEditorStore();

const publishModal = ref<Modal>();

const schema = yup.object().shape({
  versionNumber: yup
    .string()
    .required()
    .matches(
      /\d+\.\d+\.\d+/,
      "Not a valid semantic version string. Must be in MAJOR.MINOR.PATCH format."
    ),
});
type PublishFields = yup.InferType<typeof schema>;

const { serverErrors, publish, detailUrl } = useReleaseEditorAPI();

const { errors, handleSubmit, values, setValues } = useForm<PublishFields>({
  schema,
  initialValues: {},
  onSubmit: async () => {
    await publish(store.identifier, store.release.versionNumber, values);
    if (serverErrors.value.length === 0) {
      window.location.href = detailUrl(store.identifier, values.versionNumber!);
    }
  },
});

onMounted(() => {
  if (props.show) {
    publishModal.value?.show();
  }
  if (store.isInitialized) {
    setValues({ versionNumber: store.release.versionNumber });
  }
});

watch(
  () => store.isInitialized,
  () => {
    setValues({ versionNumber: store.release.versionNumber });
  }
);
</script>
