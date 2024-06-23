<template>
  <ListSidebar
    create-label="Publish a model"
    create-url="/codebases/add/"
    search-label="Apply Filters"
    data-cy="publish"
    :search-url="query"
  >
    <template #form>
      <form @submit="handleSubmit">
        <TaggerField
          class="mb-3"
          name="tags"
          label="Tags"
          type="Codebase"
          placeholder="Language, framework, etc."
        />
        <SelectField
          class="mb-3"
          name="peerReviewStatus"
          label="Peer Review Status"
          :options="peerReviewOptions"
        />
        <DatepickerField class="mb-3" name="startDate" label="Published After" />
        <DatepickerField name="endDate" label="Published Before" />
      </form>
    </template>
  </ListSidebar>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed } from "vue";
import ListSidebar from "@/components/ListSidebar.vue";
import SelectField from "@/components/form/SelectField.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import { useForm } from "@/composables/form";
import { useCodebaseAPI } from "@/composables/api";

const peerReviewOptions = [
  { value: "reviewed", label: "Reviewed" },
  { value: "not_reviewed", label: "Not Reviewed" },
  { value: "", label: "Any" },
];

const schema = yup.object({
  startDate: yup.date(),
  endDate: yup.date(),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
  peerReviewStatus: yup.string(),
});
type SearchFields = yup.InferType<typeof schema>;

const { handleSubmit, values } = useForm<SearchFields>({
  schema,
  initialValues: { peerReviewStatus: "", tags: [] },
  onSubmit: () => {
    window.location.href = query.value;
  },
});

const { searchUrl } = useCodebaseAPI();

const query = computed(() => {
  const url = new URLSearchParams(window.location.search);
  const query = url.get("query") ?? "";
  return searchUrl({
    query,
    publishedAfter: values.startDate?.toISOString(),
    publishedBefore: values.endDate?.toISOString(),
    tags: values.tags?.map(tag => tag.name),
    peerReviewStatus: values.peerReviewStatus,
  });
});
</script>
