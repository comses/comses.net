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
        <b>Please read carefully!</b> <b>Publishing</b> a release makes it possible for anyone to
        view and download it. Once a release is published, the files associated with the release
        will be <b>frozen</b> and you will no longer be able to add or remove files to the release.
        You will still be able to edit your model's metadata. If you'd like to request
        <a href="/reviews/">a peer review</a> of your model you should do that first so you may
        address any concerns raised during the peer review process that may include changes to the
        files associated with your release.
      </p>
      <p>
        Please assign a semantic version number to this release. CoMSES Net currently uses the
        <a target="_blank" href="https://semver.org">semantic versioning</a> standard, which splits
        a version number into three parts: major, minor and patch. For example, version 2.7.18 has
        major version 2, minor version 7, and patch version 18. You should increase the
        <i>major</i> version (leftmost number) if this new release is backwards incompatible with
        the previous release. You should increase the <i>minor</i> version (middle number) if this
        release introduced new features but remains backwards compatible. And finally, you should
        increase the <i>patch</i> version (rightmost number) if this release only contains bug fixes
        and remains backwards compatible (sans the bugs of course!).
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
      <p class="mb-0">Publishing a release cannot be undone. Do you want to continue?</p>
    </template>
    <template #footer>
      <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
      <button type="submit" class="btn btn-danger" form="publish-form">Publish</button>
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
