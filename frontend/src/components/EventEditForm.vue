<template>
  <form @submit="handleSubmit">
    <TextField
      class="mb-3"
      name="title"
      label="Title"
      help="A short title describing the event"
      required
    />
    <TextField
      class="mb-3"
      name="location"
      label="Location"
      help="The city and country where the event takes place"
      required
    />
    <div class="row">
      <div class="col-6">
        <DatepickerField
          class="mb-3"
          name="start_date"
          label="Start Date"
          help="The date the event begins"
          required
          :max-date="(values.end_date as Date)"
        />
      </div>
      <div class="col-6">
        <DatepickerField
          class="mb-3"
          name="end_date"
          label="End Date"
          help="The date the event ends"
          :min-date="minEndDate"
        />
      </div>
    </div>
    <div class="row">
      <div class="col-6 d-inline">
        <DatepickerField
          class="mb-3"
          name="early_registration_deadline"
          label="Early Registration Deadline"
          help="The last day for early registration of the event (inclusive)"
          :max-date="(values.start_date as Date)"
        />
      </div>
      <div class="col-6 d-inline">
        <DatepickerField
          class="mb-3"
          name="registration_deadline"
          label="Registration Deadline"
          help="The last day for registration of the event (inclusive)"
          :min-date="(values.early_registration_deadline as Date)"
          :max-date="(values.end_date as Date)"
        />
      </div>
    </div>
    <DatepickerField
      class="mb-3"
      name="submission_deadline"
      label="Submission Deadline"
      help="The last day to make a submission for the event (inclusive)"
      :min-date="(values.start_date as Date)"
      :max-date="(values.end_date as Date)"
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
      label="Event website"
      help="Link to a more detailed website for this event"
    />
    <TaggerField
      class="mb-3"
      name="tags"
      label="Tags"
      help="A list of tags to associate with an event. Tags help people search for events."
    />
    <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
    <button type="submit" class="btn btn-primary" :disabled="isLoading">
      {{ props.eventId ? "Update" : "Create" }}
    </button>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed, onBeforeUnmount, onMounted } from "vue";
import TextField from "@/components/form/TextField.vue";
import MarkdownField from "@/components/form/MarkdownField.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import FieldLabel from "@/components/form/FieldLabel.vue";
import { useForm } from "@/composables/form";
import { useEventAPI } from "@/composables/api";

const props = defineProps<{
  eventId?: number;
}>();

const schema = yup.object().shape({
  description: yup.string().required().label("Description"),
  summary: yup.string().required().label("Summary"),
  title: yup.string().required().label("Title"),
  tags: yup
    .array()
    .of(yup.object().shape({ name: yup.string().required() }))
    .label("Tags"),
  location: yup.string().required().label("Location"),
  early_registration_deadline: yup.date().nullable().label("Early registration deadline"),
  registration_deadline: yup.date().nullable().label("Registration Deadline"),
  submission_deadline: yup.date().nullable().label("Submission deadline"),
  start_date: yup.date().required().label("Start date"),
  end_date: yup.date().nullable().label("End date"),
  external_url: yup.string().url().nullable().label("External URL"),
});
type EventEditFields = yup.InferType<typeof schema>;

const { data, serverErrors, create, retrieve, update, isLoading, detailUrl } = useEventAPI();

const {
  errors,
  handleSubmit,
  values,
  setValues,
  addUnsavedAlertListener,
  removeUnsavedAlertListener,
} = useForm<EventEditFields>({
  schema,
  initialValues: {},
  showPlaceholder: isLoading,
  onSubmit: async () => {
    await createOrUpdate();
  },
});

onMounted(async () => {
  if (props.eventId) {
    await retrieve(props.eventId);
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
  if (props.eventId) {
    await update(props.eventId, values, { onSuccess });
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

const minEndDate = computed(() => {
  const dates = [
    values.start_date,
    values.submission_deadline,
    values.registration_deadline,
    values.early_registration_deadline,
  ].filter(d => !!d) as Date[];
  if (dates.length === 0) {
    return undefined;
  }
  return new Date(Math.max(...dates.map(d => d.getTime())));
});
</script>
