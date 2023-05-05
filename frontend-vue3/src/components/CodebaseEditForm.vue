<template>
  <form @submit="handleSubmit">
    <TextField
      class="mb-3"
      name="title"
      label="Title"
      help="A short title describing this computational model, limited to 300 characters"
      required
    />
    <MarkdownField
      class="mb-3"
      name="description"
      label="Description"
      help="A summary description of your model similar to an abstract. There is no limit on length but it should be kept as succinct as possible."
      required
    />
    <TextareaField
      class="mb-3"
      name="replication_text"
      label="Replication of an existing model?"
      help="Is this model a replication of a previously published computational model? Please enter a DOI or other permanent identifier to the model, or citation text. Separate multiple entries with newlines."
      :rows="3"
    />
    <TextareaField
      class="mb-3"
      name="associated_publication_text"
      label="Associated Publications"
      help="Is this model associated with any publications? Please enter a DOI or other permanent identifier, or citation text. Separate multiple entries with newlines."
      :rows="3"
    />
    <TextareaField
      class="mb-3"
      name="references_text"
      label="References"
      help="Other related publications. Please enter a DOI or other permanent identifier, or citation text. Separate multiple entries with newlines."
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
      name="repository_url"
      label="Version Control Repository URL (optional)"
      help="Is this model being developed on GitHub, BitBucket, GitLab, or other Git-based version control repository? Enter its root repository URL (e.g., https://github.com/comses/water-markets-model) for future CoMSES and Git integration."
    />
    <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
    <button type="submit" class="btn btn-primary" :disabled="isLoading">
      {{ props.codebaseId ? "Update" : "Next" }}
    </button>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { onMounted } from "vue";
import TextField from "@/components/form/TextField.vue";
import TextareaField from "@/components/form/TextareaField.vue";
import MarkdownField from "@/components/form/MarkdownField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useForm } from "@/composables/form";
import { useCodebaseAPI, useReleaseAPI } from "@/composables/api/codebase";

const props = defineProps<{
  codebaseId?: string;
}>();

const schema = yup.object().shape({
  title: yup.string().required(),
  description: yup.string().required(),
  latest_version_number: yup.string(),
  replication_text: yup.string(),
  associated_publication_text: yup.string(),
  references_text: yup.string(),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
  repository_url: yup.string().url(),
});
type CodebaseEditFields = yup.InferType<typeof schema>;

const { data, serverErrors, create, retrieve, update, isLoading, detailUrl } = useCodebaseAPI();
const { editUrl } = useReleaseAPI();

const { errors, handleSubmit, values, setValues } = useForm<CodebaseEditFields>({
  schema,
  initialValues: {},
  showPlaceholder: isLoading,
  onSubmit: async () => {
    await createOrUpdate();
  },
});

onMounted(async () => {
  if (props.codebaseId) {
    await retrieve(props.codebaseId);
    setValues(data.value);
  }
});

function nextUrl(identifier: string) {
  if (props.codebaseId) {
    return detailUrl(props.codebaseId);
  } else {
    const versionNumber = values.latest_version_number || "1.0.0";
    return editUrl(identifier, versionNumber);
  }
}

async function createOrUpdate() {
  const onSuccess = (response: any) => {
    window.location.href = nextUrl(response.data.identifier);
  };
  if (props.codebaseId) {
    await update(props.codebaseId, values, { onSuccess });
  } else {
    await create(values, { onSuccess });
  }
}
</script>
