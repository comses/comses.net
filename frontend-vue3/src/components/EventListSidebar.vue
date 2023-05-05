<template>
  <ListSidebar
    create-label="Submit an event"
    create-url="/events/add/"
    search-label="Apply Filters"
    :search-url="query"
  >
    <template #form>
      <form @submit="handleSubmit">
        <TaggerField class="mb-3" name="tags" label="Keywords" type="Event" />
        <DatepickerField class="mb-3" name="submissionDeadline" label="Submission Deadline" />
        <DatepickerField name="startDate" label="Event Start Date" />
      </form>
    </template>
  </ListSidebar>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed } from "vue";
import ListSidebar from "@/components/ListSidebar.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import { useForm } from "@/composables/form";
import { useEventAPI } from "@/composables/api/event";

const schema = yup.object({
  startDate: yup.date(),
  submissionDeadline: yup.date(),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
});
type SearchFields = yup.InferType<typeof schema>;

const { handleSubmit, values } = useForm<SearchFields>({
  schema,
  initialValues: {},
  onSubmit: () => {
    window.location.href = query.value;
  },
});

const { searchUrl } = useEventAPI();

const query = computed(() => {
  const url = new URLSearchParams(window.location.search);
  const query = url.get("query") ?? "";
  return searchUrl({
    query,
    start_date__gte: values.startDate?.toISOString(),
    submission_deadline__gte: values.submissionDeadline?.toISOString(),
    tags: values.tags?.map(tag => tag.name),
  });
});
</script>
