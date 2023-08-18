<template>
  <form @submit="handleSubmit">
    <TextField class="mb-3" name="title" label="Title" help="Job title" required />
    <MarkdownField
      class="mb-3"
      name="description"
      label="Description"
      help="Detailed description of this job position, its responsibilities, requirements, expectations, etc."
      required
    />
    <MarkdownField
      class="mb-3"
      name="summary"
      label="Summary"
      :rows="5"
      help="A short summary of the job description to be shown in search results."
      required
    >
      <template #label>
        <FieldLabel label="Summary" id-for="summary" required />
        <button type="button" class="btn btn-sm btn-link float-end p-0 mb-2" @click="summarize">
          Summarize from description
        </button>
      </template>
    </MarkdownField>
    <TextField
      class="mb-3"
      name="externalUrl"
      label="Job URL"
      help="External URL with more details for this job, including how to apply."
    />
    <DatepickerField
      class="mb-3"
      name="applicationDeadline"
      label="Application Deadline"
      help="When applications for this job are due."
      :min-date="new Date()"
    />
    <TaggerField
      class="mb-3"
      name="tags"
      label="Tags"
      help="A list of tags to associate with this job. Tags can help people find relevant jobs."
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
  applicationDeadline: yup.date().min(new Date(), "Please enter a valid date after today's date."),
  summary: yup.string().required(),
  tags: yup
    .array()
    .of(yup.object().shape({ name: yup.string().required() }))
    .min(0),
  externalUrl: yup.string().url("Please enter a valid URL").nullable(),
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
  initialValues: {
    tags: [],
  },
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
