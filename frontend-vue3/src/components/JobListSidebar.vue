<template>
  <ListSidebar
    create-label="Post a job"
    create-url="/jobs/add/"
    search-label="Apply Filters"
    :search-url="query"
  >
    <template #form>
      <form @submit="handleSubmit">
        <TaggerField class="mb-3" name="tags" label="Keywords" type="Job" />
        <DatepickerField class="mb-3" name="initialPostingDate" label="Initial post date" />
        <DatepickerField name="applicationDeadline" label="Application deadline" />
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
import { useJobAPI } from "@/composables/api/job";

const schema = yup.object({
  initialPostingDate: yup.date(),
  applicationDeadline: yup.date(),
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

const { searchUrl } = useJobAPI();

const query = computed(() => {
  const url = new URLSearchParams(window.location.search);
  const query = url.get("query") ?? "";
  return searchUrl({
    query,
    date_created__gte: values.initialPostingDate?.toISOString(),
    application_deadline__gte: values.applicationDeadline?.toISOString(),
    tags: values.tags?.map(tag => tag.name),
  });
});
</script>
