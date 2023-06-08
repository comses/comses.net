<template>
  <form @submit="handleSubmit">
    <TextField
      class="mb-3"
      name="title"
      label="Title"
      help="A short title describing the job"
      required
    />
    <MarkdownField
      class="mb-3"
      name="description"
      label="Description"
      help="Detailed information about the event"
      required
    />
    <MarkdownField
      class="mb-3"
      name="summary"
      label="Summary"
      :rows="5"
      help="A short summary of the event for display in search results. This field can be created from the description by pressing the summarize button."
      required
    >
      <template #label>
        <FieldLabel label="Summary" id-for="summary" required />
        <button type="button" class="btn btn-sm btn-link float-end p-0 mb-2" @click="summarize">
          Summarize from Description
        </button>
      </template>
    </MarkdownField>
    <TextField
      class="mb-3"
      name="external_url"
      label="Event Job URL"
      help="URL for this job on an external website"
    />
    <DatepickerField
      class="mb-3"
      name="application_deadline"
      label="Application Deadline"
      help="The last day to apply to the job"
      :min-date="new Date()"
      required
    />
    <TaggerField
      class="mb-3"
      name="tags"
      label="Tags"
      help="A list of tags to associate with a job. Tags help people search for jobs."
    />
    <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
    <button type="submit" class="btn btn-primary" :disabled="isLoading">
      {{ props.jobId ? "Update" : "Create" }}
    </button>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { onBeforeUnmount, onMounted } from "vue";
import TextField from "@/components/form/TextField.vue";
import MarkdownField from "@/components/form/MarkdownField.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import FieldLabel from "@/components/form/FieldLabel.vue";
import { useForm } from "@/composables/form";
import { useJobAPI } from "@/composables/api";

const props = defineProps<{
  jobId?: number;
}>();

const schema = yup.object().shape({
  title: yup.string().required(),
  description: yup.string().required(),
  application_deadline: yup
    .date()
    .min(new Date(), "Please enter a valid date after today's date.")
    .required(),
  summary: yup.string().required(),
  tags: yup
    .array()
    .of(yup.object().shape({ name: yup.string().required() }))
    .min(0),
  external_url: yup.string().url("Please enter a valid URL").nullable(),
});
type JobEditFields = yup.InferType<typeof schema>;

const { data, serverErrors, create, retrieve, update, isLoading, detailUrl } = useJobAPI();

const {
  errors,
  handleSubmit,
  values,
  setValues,
  addUnsavedAlertListener,
  removeUnsavedAlertListener,
} = useForm<JobEditFields>({
  schema,
  initialValues: {},
  showPlaceholder: isLoading,
  onSubmit: async () => {
    await createOrUpdate();
  },
});

onMounted(async () => {
  if (props.jobId) {
    await retrieve(props.jobId);
    setValues(data.value);
  }
  addUnsavedAlertListener();
});

onBeforeUnmount(() => {
  removeUnsavedAlertListener();
});

async function createOrUpdate() {
  const onSuccess = (response: any) => {
    window.location.href = detailUrl(response.data.id);
  };
  if (props.jobId) {
    await update(props.jobId, values, { onSuccess });
  } else {
    await create(values, { onSuccess });
  }
}

function summarize() {
  values.summary = values.description?.slice(0, 200);
  if (values.summary && values.summary.length >= 200) {
    values.summary += "...";
  }
}
</script>
