<template>
  <div>
    <button class="btn btn-primary my-1 w-100" rel="nofollow" @click="modal?.show()">
      Mirror on Github
    </button>
    <BootstrapModal
      id="github-mirror-modal"
      title="Mirror your model on Github"
      ref="modal"
      centered
    >
      <template #body>
        <form @submit="handleSubmit" id="github-mirror-form">
          <TextField class="mb-3" name="repoName" label="Repository Name" required />
          <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
        </form>
      </template>
      <template #footer>
        <button type="button" data-bs-dismiss="modal" class="btn btn-outline-gray">Cancel</button>
        <button type="submit" form="github-mirror-form" class="btn btn-success">Mirror</button>
      </template>
    </BootstrapModal>
  </div>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { ref } from "vue";
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";
import TextField from "@/components/form/TextField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useForm } from "@/composables/form";
import { useCodebaseAPI } from "@/composables/api";

export interface GithubMirrorModalProps {
  identifier: string;
  defaultRepoName: string;
}

const props = defineProps<GithubMirrorModalProps>();

const modal = ref<Modal>();

const schema = yup.object().shape({
  repoName: yup.string().max(100).required(),
});
type GithubMirrorModalFields = yup.InferType<typeof schema>;

const { serverErrors, githubMirror } = useCodebaseAPI();

const { errors, handleSubmit, values } = useForm<GithubMirrorModalFields>({
  schema,
  initialValues: {
    repoName: props.defaultRepoName,
  },
  onSubmit: async () => {
    await githubMirror(props.identifier, values.repoName!, {
      onSuccess: () => {
        modal.value?.hide();
        window.location.reload();
      },
    });
  },
});
</script>
