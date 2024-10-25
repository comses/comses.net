<template>
  <div>
    <button
      class="btn btn-sm btn-outline-secondary w-100-with-icon my-1"
      rel="nofollow"
      @click="modal?.show()"
    >
      <i class="icon-left fas fa-arrow-up"></i>
      Mirror on Github
    </button>
    <BootstrapModal
      id="github-mirror-modal"
      title="Mirror your model on Github"
      ref="modal"
      centered
    >
      <template #body>
        <p>
          This will transform your model into a git repository and archive it on GitHub under a
          central CoMSES Model Library organization.
          <a href="/github" target="_blank"
            >Learn more <i class="small fas fa-chevron-right"></i
          ></a>
        </p>
        <form @submit="handleSubmit" id="github-mirror-form">
          <TextField class="mb-3" name="repoName" label="Repository Name" required />
          <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
          <div v-if="successMessage" class="alert alert-info alert-dismissible fade show mb-0 mt-3">
            {{ successMessage }}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" />
          </div>
        </form>
      </template>
      <template #footer>
        <button type="button" data-bs-dismiss="modal" class="btn btn-outline-gray">Cancel</button>
        <button
          type="submit"
          form="github-mirror-form"
          class="btn btn-primary"
          :disabled="isLoading"
        >
          <span v-if="isLoading"> <i class="fas fa-spinner fa-spin me-1"></i> Loading...</span>
          <span v-else>Create Mirror</span>
        </button>
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

const { serverErrors, githubMirror, data: successMessage, isLoading } = useCodebaseAPI();

const { errors, handleSubmit, values } = useForm<GithubMirrorModalFields>({
  schema,
  initialValues: {
    repoName: props.defaultRepoName,
  },
  onSubmit: async () => {
    await githubMirror(props.identifier, values.repoName!);
  },
});
</script>
