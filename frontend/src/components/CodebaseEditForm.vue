<template>
  <form :id="id" @submit="handleSubmit">
    <TextField
      class="mb-3"
      name="title"
      label="Title"
      help="A short title describing this computational model, limited to 300 characters"
      data-cy="codebase-title"
      required
    />
    <HoneypotField />
    <MarkdownField
      class="mb-3"
      name="description"
      label="Description"
      help="A summary description of your model similar to an abstract. There is no limit on length but it should be kept as succinct as possible."
      data-cy="codebase-description"
      required
    />
    <TextareaField
      class="mb-3"
      name="replicationText"
      label="Replication of an existing model?"
      help="Is this model a replication of a previously published computational model? Please enter a DOI or other permanent identifier to the model, or citation text. Separate multiple entries with newlines."
      data-cy="codebase-replication-text"
      :rows="3"
    />
    <TextareaField
      class="mb-3"
      name="associatedPublicationText"
      label="Associated Publications"
      help="Is this model associated with any publications? Please enter a DOI or other permanent identifier, or citation text. Separate multiple entries with newlines."
      data-cy="codebase-associated-publications"
      :rows="3"
    />
    <TextareaField
      class="mb-3"
      name="referencesText"
      label="References"
      help="Other related publications. Please enter a DOI or other permanent identifier, or citation text. Separate multiple entries with newlines."
      data-cy="codebase-references"
      :rows="3"
    />
    <TaggerField
      class="mb-3"
      name="tags"
      label="Tags"
      help="Add tags to categorize your model and make it more discoverable. Press enter after entering each tag."
    />
    <TextField
      class="mb-3"
      name="repositoryUrl"
      label="Version Control Repository URL (reference only)"
      help="Link to your model's version control repository (GitHub, GitLab, BitBucket, etc.). For reference only, you can connect a GitHub repository with the button below, or later on."
    />
    <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
    <div v-if="!asModal" class="d-flex gap-2">
      <button type="submit" class="btn btn-primary" :disabled="isLoading" data-cy="next">
        {{ props.identifier ? "Update" : "Continue to upload model" }}
      </button>
      <button
        v-if="!props.identifier"
        type="submit"
        class="btn btn-outline-gray"
        :disabled="isLoading"
        data-cy="go-github-config"
        @click="goToGithubConfig = true"
      >
        Import model from GitHub
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { onBeforeUnmount, onMounted, ref } from "vue";
import TextField from "@/components/form/TextField.vue";
import TextareaField from "@/components/form/TextareaField.vue";
import MarkdownField from "@/components/form/MarkdownField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import HoneypotField from "@/components/form/HoneypotField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useForm } from "@/composables/form";
import { type RequestOptions, useCodebaseAPI, useReleaseEditorAPI } from "@/composables/api";
import { useGitRemotesAPI } from "@/composables/api/git";

const props = withDefaults(
  defineProps<{
    identifier?: string;
    asModal?: boolean;
    id?: string;
  }>(),
  {
    asModal: false,
    id: "edit-codebase-form",
  }
);

const emit = defineEmits(["success"]);

const schema = yup.object().shape({
  title: yup.string().required(),
  description: yup.string().required(),
  latestVersionNumber: yup.string(),
  replicationText: yup.string(),
  associatedPublicationText: yup.string(),
  referencesText: yup.string(),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
  repositoryUrl: yup.string().url(),
});
type CodebaseEditFields = yup.InferType<typeof schema>;

const { data, serverErrors, create, retrieve, update, isLoading, detailUrl } = useCodebaseAPI();
const { editUrl } = useReleaseEditorAPI();
const goToGithubConfig = ref(false);

const {
  errors,
  handleSubmit,
  values,
  setValuesWithLoadTime,
  addUnsavedAlertListener,
  removeUnsavedAlertListener,
} = useForm<CodebaseEditFields>({
  schema,
  initialValues: {
    tags: [],
  },
  showPlaceholder: isLoading,
  onSubmit: async () => {
    await createOrUpdate();
  },
});

onMounted(async () => {
  if (props.identifier) {
    await retrieve(props.identifier);
    setValuesWithLoadTime(data.value);
  }
  addUnsavedAlertListener();
});

onBeforeUnmount(() => {
  removeUnsavedAlertListener();
});

function githubConfigUrl(identifier: string) {
  const { detailUrl: gitDetailUrl } = useGitRemotesAPI(identifier);
  return gitDetailUrl("");
}

function redirectUrl(identifier: string, useGithubConfig: boolean) {
  if (useGithubConfig) return githubConfigUrl(identifier);
  if (props.identifier) return detailUrl(props.identifier);
  const versionNumber = values.latestVersionNumber || "1.0.0";
  return editUrl(identifier, versionNumber);
}

async function createOrUpdate() {
  const useGithubConfig = goToGithubConfig.value && !props.identifier;
  const onSuccess = (response: any) => {
    const destination = useGithubConfig;
    if (props.asModal) {
      emit("success");
    } else {
      window.location.href = redirectUrl(response.data.identifier, destination);
    }
  };
  const requestOptions: RequestOptions = { onSuccess };
  if (useGithubConfig) {
    requestOptions.config = { params: { initial_version: "0.0.1" } };
  }
  try {
    if (props.identifier) {
      await update(props.identifier, values, requestOptions);
    } else {
      await create(values, requestOptions);
    }
  } finally {
    goToGithubConfig.value = false;
  }
}
</script>
