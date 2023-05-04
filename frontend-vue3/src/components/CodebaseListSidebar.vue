<template>
  <ListSidebar
    create-label="Archive a model"
    create-url="/codebases/add/"
    search-label="Search"
    :search-url="query"
  >
    <template #form>
      <form @submit="handleSubmit">
        <TextField class="mb-3" name="keywords" label="Keywords" @keyup.enter="search" />
        <DatepickerField class="mb-3" name="startDate" label="Published After" />
        <DatepickerField class="mb-3" name="endDate" label="Published Before" />
        <TaggerField class="mb-3" name="tags" label="Tags" type="Codebase" />
        <SelectField
          class="mb-3"
          name="peerReviewStatus"
          label="Peer Review Status"
          :options="peerReviewOptions"
        />
      </form>
    </template>
  </ListSidebar>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed } from "vue";
import ListSidebar from "@/components/ListSidebar.vue";
import TextField from "@/components/form/TextField.vue";
import SelectField from "@/components/form/SelectField.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import { useForm } from "@/composables/form";
import { useCodebaseAPI } from "@/composables/api/codebase";

const peerReviewOptions = [
  { value: "reviewed", label: "Reviewed" },
  { value: "not_reviewed", label: "Not Reviewed" },
  { value: "", label: "Any" },
];

const schema = yup.object({
  keywords: yup.string(),
  startDate: yup.date(),
  endDate: yup.date(),
  tags: yup.array().of(yup.object().shape({ name: yup.string().required() })),
  peerReviewStatus: yup.string(),
});
type SearchFields = yup.InferType<typeof schema>;

const { handleSubmit, values } = useForm<SearchFields>({
  schema,
  initialValues: { peerReviewStatus: "" },
  onSubmit: () => {
    window.location.href = query.value;
  },
});

const { searchUrl } = useCodebaseAPI();

const query = computed(() => {
  return searchUrl({
    query: values.keywords,
    published_after: values.startDate?.toISOString(),
    published_before: values.endDate?.toISOString(),
    tags: values.tags?.map(tag => tag.name),
    peer_review_status: values.peerReviewStatus,
  });
});

function search() {
  window.location.href = query.value;
}
</script>
