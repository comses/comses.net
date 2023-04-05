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
          <FormContext :schema="schema" :initial-values="initialValues" @submit="onSubmit">
            <FormTextInput class="mb-3" v-bind="props.keywords" />
            <FormDatePicker class="mb-3" v-bind="props.startDate" />
            <FormDatePicker class="mb-3" v-bind="props.endDate" />
            <FormTagger class="mb-3" v-bind="props.tags" />
            <FormSelect class="mb-3" v-bind="props.peerReviewStatus" />
          </FormContext>
        </div>
      </div>
    </template>
  </BaseSearch>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BaseSearch from "@/components/BaseSearch.vue";
import FormContext from "@/components/form/FormContext.vue";
import FormTextInput from "@/components/form/FormTextInput.vue";
import FormSelect from "@/components/form/FormSelect.vue";
import FormDatePicker from "@/components/form/FormDatePicker.vue";
import FormTagger from "@/components/form/FormTagger.vue";
import { useFormBuilder } from "@/composables/form";
import type { Values } from "@/components/form/FormContext.vue";

const { schema, initialValues, props } = useFormBuilder({
  keywords: {
    props: {
      name: "keywords",
      label: "Keywords",
    },
  },
  startDate: {
    props: {
      name: "startDate",
      label: "Published After",
    },
  },
  endDate: {
    props: {
      name: "endDate",
      label: "Published Before",
    },
  },
  tags: {
    props: {
      name: "tags",
      label: "Tags",
      placeholder: "Type to add tags",
    },
  },
  peerReviewStatus: {
    props: {
      name: "peerReviewStatus",
      label: "Peer Review Status",
      options: [
        { value: "reviewed", label: "Reviewed" },
        { value: "not_reviewed", label: "Not Reviewed" },
        { value: "", label: "Any" },
      ],
    },
    initialValue: "",
  },
});

const query = computed(() => {
  const params = new URLSearchParams();
  params.append("text", initialValues.text);
  params.append("email", initialValues.email);
  params.append("terms", initialValues.terms);
  params.append("number", initialValues.number);
  params.append("date", initialValues.date);
  params.append("tags", initialValues.tags);
  return `/codebases/search/?${params.toString()}`;
});

async function onSubmit(values: Values) {
  console.log(values);
}
</script>
