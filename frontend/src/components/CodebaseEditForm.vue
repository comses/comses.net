<template>
  <form :id="id" @submit="handleSubmit">
    <TextField
      class="mb-3"
      name="title"
      label="Title"
      help="A short title describing this computational model, limited to 300 characters"
      required
    />
    <HoneypotField />
    <MarkdownField
      class="mb-3"
      name="description"
      label="Description"
      help="A summary description of your model similar to an abstract. There is no limit on length but it should be kept as succinct as possible."
      required
    />
    <TextareaField
      class="mb-3"
      name="replicationText"
      label="Replication of an existing model?"
      help="Is this model a replication of a previously published computational model? Please enter a DOI or other permanent identifier to the model, or citation text. Separate multiple entries with newlines."
      :rows="3"
    />
    <TextareaField
      class="mb-3"
      name="associatedPublicationText"
      label="Associated Publications"
      help="Is this model associated with any publications? Please enter a DOI or other permanent identifier, or citation text. Separate multiple entries with newlines."
      :rows="3"
    />
    <TextareaField
      class="mb-3"
      name="referencesText"
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
      name="repositoryUrl"
      label="Version Control Repository URL (optional)"
      help="Is this model being developed on GitHub, BitBucket, GitLab, or other Git-based version control repository? Enter its root repository URL (e.g., https://github.com/comses/water-markets-model) for future CoMSES and Git integration."
    />
    <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
    <button v-if="!asModal" type="submit" class="btn btn-primary" :disabled="isLoading">
      {{ props.identifier ? "Update" : "Next" }}
    </button>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { onBeforeUnmount, onMounted } from "vue";
import TextField from "@/components/form/TextField.vue";
import TextareaField from "@/components/form/TextareaField.vue";
import MarkdownField from "@/components/form/MarkdownField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import HoneypotField from "@/components/form/HoneypotField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useForm } from "@/composables/form";
import { useCodebaseAPI, useReleaseEditorAPI } from "@/composables/api";

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
    console.log(data.value);
    setValuesWithLoadTime(data.value);
  }
  addUnsavedAlertListener();
});

onBeforeUnmount(() => {
  removeUnsavedAlertListener();
});

function nextUrl(identifier: string) {
  if (props.identifier) {
    return detailUrl(props.identifier);
  } else {
    const versionNumber = values.latestVersionNumber || "1.0.0";
    return editUrl(identifier, versionNumber);
  }
}

async function createOrUpdate() {
  const onSuccess = (response: any) => {
    if (props.asModal) {
      emit("success");
    } else {
      window.location.href = nextUrl(response.data.identifier);
    }
  };
  if (props.identifier) {
    await update(props.identifier, values, { onSuccess });
  } else {
    await create(values, { onSuccess });
  }
}
</script>
