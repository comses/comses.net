<template>
  <ListSidebar
    create-label="Publish a model"
    create-url="/codebases/add/"
    search-label="Apply Filters"
    data-cy="publish"
    :clear-all-filters="clearAllFilters"
    :is-filter-changed="isFilterChanged"
    :search-url="query"
  >
    <template #form>
      <form @submit.prevent="handleSubmit">
        <div class="mb-3">
          <label class="form-label fw-bold">Peer Review Status</label>
          <div v-for="option in peerReviewOptions" :key="option.value" class="form-check">
            <input
              class="form-check-input"
              type="radio"
              :id="option.value"
              :value="option.value"
              v-model="values.peerReviewStatus"
            />
            <label class="form-check-label" :for="option.value">
              {{ option.label }}
            </label>
          </div>
        </div>

        <div class="mb-3" v-if="parsedLanguageFacets.length > 0">
          <label class="form-label fw-bold"> Programming Languages </label>
          <div class="row">
            <div v-for="lang in parsedLanguageFacets" :key="lang.value" class="col-12 col-md-12">
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  :id="lang.value"
                  :value="lang.value"
                  v-model="values.programmingLanguages"
                />
                <label class="form-check-label" :for="lang.value">
                  {{ lang.label }}
                </label>
              </div>
            </div>
          </div>
        </div>

        <div class="row mb-3 fw-bold">
          <DatepickerField name="startDate" label="Published After" class="col-12 col-md-12 py-2" />
          <DatepickerField name="endDate" label="Published Before" class="col-12 col-md-12 py-2" />
        </div>

        <TaggerField
          class="mb-1"
          name="tags"
          label="Tags"
          type="Codebase"
          placeholder="Language, framework, etc."
        />
      </form>
    </template>
  </ListSidebar>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { onMounted, computed } from "vue";
import { defineProps } from "vue";
import { isEqual } from "lodash-es";
import ListSidebar from "@/components/ListSidebar.vue";
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
  startDate: yup.date().nullable(),
  endDate: yup.date().nullable(),
  tags: yup.array().of(
    yup.object().shape({
      name: yup.string().required(),
    })
  ),
  peerReviewStatus: yup.string(),
  programmingLanguages: yup.array().of(yup.string().required()),
  ordering: yup.string(),
});

type SearchFields = yup.InferType<typeof schema>;
const { handleSubmit, values } = useForm<SearchFields>({
  schema,
  initialValues: {},
  onSubmit: () => {
    window.location.href = query.value;
  },
});

const { searchUrl } = useCodebaseAPI();

type LanguageFacet = {
  value: string;
  label: string;
};
const props = defineProps<{
  languageFacets?: Record<string, number>;
}>();

let parsedLanguageFacets: LanguageFacet[] = [];

const initialFilterValues = {
  value: { ...values },
};

onMounted(() => {
  if (props.languageFacets) {
    const localLanguageFacets = { ...props.languageFacets };
    console.log(localLanguageFacets);
    parsedLanguageFacets = Object.entries(localLanguageFacets)
      .sort(([, valueA], [, valueB]) => valueB - valueA) // Sort by value in descending order
      .map(([name, value]) => ({ value: name, label: `${name} (${value})` }));
  } else {
    console.warn("languageFacets is undefined");
  }
  initializeFilterValues();
});

const initializeFilterValues = () => {
  const urlParams = new URLSearchParams(window.location.search);
  values.peerReviewStatus = urlParams.get("peerReviewStatus") || "";
  values.programmingLanguages = urlParams.getAll("programmingLanguages").sort() || [];
  values.tags = urlParams.getAll("tags").map(tag => ({ name: tag })) || [];
  values.startDate = urlParams.get("publishedAfter")
    ? new Date(urlParams.get("publishedAfter")!)
    : null;
  values.endDate = urlParams.get("publishedBefore")
    ? new Date(urlParams.get("publishedBefore")!)
    : null;
  values.ordering = urlParams.get("ordering") || "-first_published_at";

  initialFilterValues.value = { ...values };
};

const isFilterChanged = computed(() => {
  const currentValues = {
    ...values,
    programmingLanguages: sortedProgrammingLanguages.value, // Use sorted values for comparison
  };
  return !isEqual(currentValues, initialFilterValues.value);
});

// Computed property for sorted programming languages
const sortedProgrammingLanguages = computed(() => {
  return values.programmingLanguages?.slice().sort(); // Sort the programming languages
});

const query = computed(() => {
  const url = new URLSearchParams(window.location.search);
  const searchQuery = url.get("query") ?? "";

  return searchUrl({
    query: searchQuery,
    publishedAfter: values.startDate?.toISOString(),
    publishedBefore: values.endDate?.toISOString(),
    tags: values.tags?.map(tag => tag.name),
    peerReviewStatus: values.peerReviewStatus,
    programmingLanguages: values.programmingLanguages,
    ordering: values.ordering,
  });
});

const clearAllFilters = () => {
  values.peerReviewStatus = "";
  values.programmingLanguages = [];
  values.tags = [];
  values.startDate = null;
  values.endDate = null;
  values.ordering = "-first_published_at";
  window.location.href = query.value;
};
</script>
