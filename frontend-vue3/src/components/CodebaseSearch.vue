<template>
  <BaseSearch
    submit-label="Archive a model"
    submit-url="/codebases/add/"
    search-label="Search"
    :search-url="query"
  >
    <template #form>
      <div class="card-metadata">
        <h2 class="title">Search</h2>
        <div class="card-body">
          <form @submit="handleSubmit">
            <FormTextInput class="mb-3" name="keywords" label="Keywords" />
            <FormDatePicker class="mb-3" name="startDate" label="Published After" />
            <FormDatePicker class="mb-3" name="endDate" label="Published Before" />
            <FormTagger class="mb-3" name="tags" label="Tags" type="Codebase" />
            <FormSelect
              class="mb-3"
              name="peerReviewStatus"
              label="Peer Review Status"
              :options="peerReviewOptions"
            />
          </form>
        </div>
      </div>
    </template>
  </BaseSearch>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed } from "vue";
import BaseSearch from "@/components/BaseSearch.vue";
import FormTextInput from "@/components/form/FormTextInput.vue";
import FormSelect from "@/components/form/FormSelect.vue";
import FormDatePicker from "@/components/form/FormDatePicker.vue";
import FormTagger from "@/components/form/FormTagger.vue";
import { useForm } from "@/composables/form";
import { useCodebaseAPI } from "@/composables/api/codebase";
import type { Tags } from "@/composables/api/tags";

interface SearchFields {
  keywords: string;
  startDate: string;
  endDate: string;
  tags: Tags;
  peerReviewStatus: string;
}

const initialValues: Partial<SearchFields> = {
  peerReviewStatus: "",
};

const schema = yup.object({
  keywords: yup.string().required(),
  startDate: yup.string(),
  peerReviewStatus: yup.string(),
});

const peerReviewOptions = [
  { value: "reviewed", label: "Reviewed" },
  { value: "not_reviewed", label: "Not Reviewed" },
  { value: "", label: "Any" },
];

const { handleSubmit, values } = useForm<SearchFields>({
  initialValues,
  schema,
  onSubmit: values => {
    console.log(values);
  },
});

const { searchUrl } = useCodebaseAPI();

const query = computed(() => {
  return searchUrl({
    query: values.keywords,
    published_after: values.startDate,
    published_before: values.endDate,
    tags: values.tags?.map(tag => tag.name),
    peer_review_status: values.peerReviewStatus,
  });
});
</script>
