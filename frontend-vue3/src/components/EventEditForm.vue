<template>
  <form @submit="handleSubmit">
    <FormTextInput
      class="mb-3"
      name="title"
      label="Title"
      help="A short title describing the event"
      indicate-required
    />
    <FormTextInput
      class="mb-3"
      name="location"
      label="Location"
      help="The city and country where the event takes place"
      indicate-required
    />
    <div class="row">
      <div class="col-6">
        <FormDatePicker
          class="mb-3"
          name="start_date"
          label="Start Date"
          help="The date the event begins"
          indicate-required
        />
      </div>
      <div class="col-6">
        <FormDatePicker
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
        <FormDatePicker
          class="mb-3"
          name="early_registration_deadline"
          label="Early Registration Deadline"
          help="The last day for early registration of the event (inclusive)"
        />
      </div>
      <div class="col-6 d-inline">
        <FormDatePicker
          class="mb-3"
          name="registration_deadline"
          label="Registration Deadline"
          help="The last day for registration of the event (inclusive)"
          :min-date="(values.early_registration_deadline as Date)"
        />
      </div>
    </div>
    <FormDatePicker
      class="mb-3"
      name="submission_deadline"
      label="Submission Deadline"
      help="The last day to make a submission for the event (inclusive)"
      :min-date="(values.start_date as Date)"
    />
    <FormTextArea
      class="mb-3"
      name="description"
      label="Description"
      help="Detailed information about the event"
      indicate-required
    />
    <!-- FIXME: use markdown field when implemented -->
    <FormTextArea
      class="mb-3"
      name="summary"
      label="Summary"
      help="A short summary of the event for display in search results. This field can be created from the description by pressing the summarize button."
      indicate-required
    />
    <FormTextInput
      class="mb-3"
      name="external_url"
      label="Event website"
      help="Link to a more detailed website for this event"
    />
    <FormTagger
      class="mb-3"
      name="tags"
      label="Tags"
      help="A list of tags to associate with an event. Tags help people search for events."
    />
    <button type="submit" class="btn btn-primary" :disabled="isLoading">
      {{ props.eventId ? "Update" : "Create" }}
    </button>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed, onMounted } from "vue";
import FormTextInput from "@/components/form/FormTextInput.vue";
import FormTextArea from "@/components/form/FormTextArea.vue";
import FormDatePicker from "@/components/form/FormDatePicker.vue";
import FormTagger from "@/components/form/FormTagger.vue";
import { useForm } from "@/composables/form";
import { useEventAPI } from "@/composables/api/event";

const props = defineProps<{
  eventId?: number;
}>();

const schema = yup.object().shape({
  description: yup.string().required(),
  summary: yup.string().required(),
  title: yup.string().required(),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
  location: yup.string().required(),
  early_registration_deadline: yup.date().nullable().label("early registration deadline"),
  registration_deadline: yup.date().nullable().label("Registration Deadline"),
  submission_deadline: yup.date().nullable().label("submission deadline"),
  start_date: yup.date().required().label("start date"),
  end_date: yup.date().nullable(),
  external_url: yup.string().url().nullable(),
});
type EventEditFields = yup.InferType<typeof schema>;

const { data, error, create, retrieve, update, isLoading, detailUrl } = useEventAPI();

const { handleSubmit, values, setValues } = useForm<EventEditFields>({
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
    if (error.value) {
      console.error(error.value);
    } else {
      setValues(data.value);
    }
  }
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
