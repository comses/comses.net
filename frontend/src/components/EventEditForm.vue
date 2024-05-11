<template>
  <form @submit="handleSubmit">
    <TextField class="mb-3" name="title" label="Title" help="The name of this event" required />
    <HoneypotField />
    <TextField
      class="mb-3"
      name="location"
      label="Location"
      help="Please enter the city and country hosting the event, or 'online' or 'hybrid' for fully virtual or mixed events."
      required
    />
    <div class="row">
      <div class="col-6">
        <DatepickerField
          class="mb-3"
          name="startDate"
          label="Start Date"
          help="The date this event begins"
          required
          :max-date="(values.endDate as Date)"
        />
      </div>
      <div class="col-6">
        <DatepickerField
          class="mb-3"
          name="endDate"
          label="End Date"
          help="The date this event ends"
          :min-date="minEndDate"
        />
      </div>
    </div>
    <div class="row">
      <div class="col-6 d-inline">
        <DatepickerField
          class="mb-3"
          name="earlyRegistrationDeadline"
          label="Early Registration Deadline"
          help="The last day for early registration for this event (inclusive)"
          :max-date="(values.startDate as Date)"
        />
      </div>
      <div class="col-6 d-inline">
        <DatepickerField
          class="mb-3"
          name="registrationDeadline"
          label="Registration Deadline"
          help="The last day to register for this event (inclusive)"
          :min-date="(values.earlyRegistrationDeadline as Date)"
          :max-date="(values.endDate as Date)"
        />
      </div>
    </div>
    <DatepickerField
      class="mb-3"
      name="submissionDeadline"
      label="Submission Deadline"
      help="The last day to make a submission for this event (inclusive)"
      :max-date="(values.endDate as Date)"
    />
    <MarkdownField
      class="mb-3"
      name="description"
      label="Description"
      help="A detailed description of this event."
      required
    />
    <MarkdownField
      class="mb-3"
      name="summary"
      label="Summary"
      :rows="5"
      help="A short summary of this event for display in search results."
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
      label="Event website"
      help="URL to this event's website where people can register, etc."
    />
    <TaggerField
      class="mb-3"
      name="tags"
      label="Tags"
      help="A list of tags to associate with this event. Tags can help people find relevant events."
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
import HoneypotField from "@/components/form/HoneypotField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import FieldLabel from "@/components/form/FieldLabel.vue";
import { useForm } from "@/composables/form";
import { useEventAPI } from "@/composables/api";
import { useFormTimer, type TimerFields } from "@/composables/spam";

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
  earlyRegistrationDeadline: yup.date().nullable().label("Early registration deadline"),
  registrationDeadline: yup.date().nullable().label("Registration Deadline"),
  submissionDeadline: yup.date().nullable().label("Submission deadline"),
  startDate: yup.date().required().label("Start date"),
  endDate: yup.date().nullable().label("End date"),
  externalUrl: yup.string().url().nullable().label("External URL"),
});
type EventEditFields = yup.InferType<typeof schema>;

const { data, serverErrors, create, retrieve, update, isLoading, detailUrl } = useEventAPI();

const { loadedTime, getSubmitTime } = useFormTimer();

const {
  errors,
  handleSubmit,
  values,
  setValues,
  addUnsavedAlertListener,
  removeUnsavedAlertListener,
} = useForm<EventEditFields & TimerFields>({
  schema,
  initialValues: {
    tags: [],
  },
  showPlaceholder: isLoading,
  onSubmit: async () => {
    values.loadedTime = loadedTime;
    values.submitTime = getSubmitTime();
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
    values.startDate,
    values.submissionDeadline,
    values.registrationDeadline,
    values.earlyRegistrationDeadline,
  ].filter(d => !!d) as Date[];
  if (dates.length === 0) {
    return undefined;
  }
  return new Date(Math.max(...dates.map(d => d.getTime())));
});
</script>
