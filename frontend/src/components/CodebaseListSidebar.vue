<template>
  <ListSidebar
    create-label="Publish a model"
    create-url="/codebases/add/"
    search-label="Apply Filters"
    data-cy="publish"
    :clear-all-filters="clearAllFilters"
    :search-url="query"
  >
    <template #form>
      <form @submit.prevent="handleSubmit">
        <div class="mb-3" v-if="selectedFilters.length > 0">
          <label class="form-label fw-bold"
            >Selected Filters
            <a @click="clearAllFilters" class="p-2" aria-label="clear all">Clear all</a>
          </label>
          <div class="d-flex flex-wrap gap-2">
            <span
              v-for="filter in selectedFilters"
              :key="filter.key"
              class="badge bg-light text-dark text-wrap d-flex align-items-center"
            >
              {{ filter.label }}
              <button
                @click="removeFilter(filter.key)"
                class="btn-close ms-2"
                aria-label="Close"
              ></button>
            </span>
          </div>
          <hr class="hr" />
        </div>

        <div class="mb-3">
          <label class="form-label fw-bold">Peer Review Status</label>
          <div v-for="option in peerReviewOptions" :key="option.value" class="form-check">
            <input
              class="form-check-input"
              type="radio"
              :id="option.value"
              :value="option.value"
              v-model="values.peerReviewStatus"
              @change="updateFilters"
            />
            <label class="form-check-label" :for="option.value">
              {{ option.label }}
            </label>
          </div>
        </div>

        <div class="mb-3">
          <label v-if="parsedLanguageFacets.length > 0" class="form-label fw-bold">
            Programming Languages
          </label>
          <div class="row">
            <div v-for="lang in parsedLanguageFacets" :key="lang.value" class="col-12 col-md-12">
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  :id="lang.value"
                  :value="lang.value"
                  v-model="values.programmingLanguages"
                  @change="updateFilters"
                />
                <label class="form-check-label" :for="lang.value">
                  {{ lang.label }}
                </label>
              </div>
            </div>
          </div>
        </div>

        <div class="row mb-4 fw-bold">
          <DatepickerField name="startDate" label="Published After" class="col-12 col-md-6" />
          <DatepickerField name="endDate" label="Published Before" class="col-12 col-md-6" />
        </div>

        <TaggerField
          class="mb-3"
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
import { onMounted, computed, ref, watch } from "vue";
import { defineProps } from "vue";
import ListSidebar from "@/components/ListSidebar.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import { useForm } from "@/composables/form";
import { useCodebaseAPI } from "@/composables/api";

const props = defineProps<{
  languageFacets?: Record<string, number>;
}>();

// Define a variable to store the parsed language facets
let parsedLanguageFacets: { value: string; label: string }[] = [];

onMounted(() => {
  if (props.languageFacets) {
    const localLanguageFacets = { ...props.languageFacets };

    parsedLanguageFacets = Object.entries(localLanguageFacets)
      .sort(([, valueA], [, valueB]) => valueB - valueA) // Sort by value in descending order
      .map(([name, value]) => ({ value: name, label: `${name} (${value})` }));
  } else {
    console.warn("languageFacets is undefined");
  }

  initializeFilters();
  watch([() => values.startDate, () => values.endDate, () => values.tags], updateFilters);
});

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
  initialValues: {
    peerReviewStatus: "",
    programmingLanguages: [],
    tags: [],
    startDate: null,
    endDate: null,
    ordering: "",
  },
  onSubmit: () => {
    window.location.href = query.value;
  },
});

const { searchUrl } = useCodebaseAPI();
const selectedFilters = ref<Array<{ key: string; label: string }>>([]);

const updateFilters = () => {
  selectedFilters.value = [
    // Peer Review Status
    ...(values.peerReviewStatus
      ? [
          {
            key: `peerReview_${values.peerReviewStatus}`,
            label: `Peer Review: ${
              peerReviewOptions.find(o => o.value === values.peerReviewStatus)?.label ||
              values.peerReviewStatus
            }`,
          },
        ]
      : []),

    // Programming Languages
    ...(values.programmingLanguages && values.programmingLanguages.length > 0
      ? values.programmingLanguages.map(lang => ({
          key: `lang_${lang}`,
          label: `Language: ${
            parsedLanguageFacets.find(l => l.value === lang)?.value || `${lang}`
          }`,
        }))
      : []),

    // Start Date
    ...(values.startDate
      ? [{ key: "startDate", label: `After: ${values.startDate.toLocaleDateString()}` }]
      : []),

    // End Date
    ...(values.endDate
      ? [{ key: "endDate", label: `Before: ${values.endDate.toLocaleDateString()}` }]
      : []),

    // Tags
    ...(values.tags && values.tags.length > 0
      ? values.tags.map(tag => ({
          key: `tag_${tag.name}`,
          label: `Tag: ${tag.name}`,
        }))
      : []),
  ];
};

const removeFilter = (key: string) => {
  if (key.startsWith("peerReview_")) {
    values.peerReviewStatus = "";
  } else if (key.startsWith("lang_")) {
    values.programmingLanguages =
      values.programmingLanguages?.filter(lang => `lang_${lang}` !== key) || [];
  } else if (key === "startDate") {
    values.startDate = null;
  } else if (key === "endDate") {
    values.endDate = null;
  } else if (key.startsWith("tag_")) {
    const tagName = key.slice(4); // Remove 'tag_' prefix
    values.tags = values.tags?.filter(tag => tag.name !== tagName) || [];
  }
  updateFilters();
};

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

const initializeFilters = () => {
  const urlParams = new URLSearchParams(window.location.search);
  values.peerReviewStatus = urlParams.get("peerReviewStatus") || "";
  values.programmingLanguages = urlParams.getAll("programmingLanguages") || [];
  values.tags = urlParams.getAll("tags").map(tag => ({ name: tag })) || [];
  values.startDate = urlParams.get("publishedAfter")
    ? new Date(urlParams.get("publishedAfter")!)
    : null;
  values.endDate = urlParams.get("publishedBefore")
    ? new Date(urlParams.get("publishedBefore")!)
    : null;
  values.ordering = urlParams.get("ordering") || "-first_published_at";

  updateFilters();
};

const clearAllFilters = () => {
  values.peerReviewStatus = "";
  values.programmingLanguages = [];
  values.tags = [];
  values.startDate = null;
  values.endDate = null;
  values.ordering = "-first_published_at";

  updateFilters();

  window.location.href = query.value;
};

defineExpose({ clearAllFilters });
</script>
