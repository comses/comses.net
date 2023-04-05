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
            <FormTagger class="mb-3" name="tags" label="Tags" />
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

interface SearchFields {
  keywords: string;
  startDate: Date;
  endDate: Date;
  tags: string[];
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

const query = computed(() => {
  // const params = new URLSearchParams();
  // params.append("text", initialValues.text);
  // params.append("email", initialValues.email);
  // params.append("terms", initialValues.terms);
  // params.append("number", initialValues.number);
  // params.append("date", initialValues.date);
  // params.append("tags", initialValues.tags);
  // return `/codebases/search/?${params.toString()}`;
  return `/codebases/search/?${values.keywords}`;
});
</script>
