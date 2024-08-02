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
        <TaggerField
          class="mb-3 py-2"
          name="tags"
          label="Tags"
          type="Codebase"
          placeholder="Language, framework, etc."
        />

        <div class="mb-3">
          <label class="form-label fw-bold py-2">Peer Review Status</label>
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
          <label v-if="programmingLanguages.length > 0" class="form-label fw-bold py-2">
            Programming Languages
          </label>
          <div class="row">
            <div v-for="lang in programmingLanguages" :key="lang.value" class="col-12 col-md-12">
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
          <DatepickerField name="startDate" label="Published After" />
        </div>
        <div class="row mb-4 fw-bold">
          <DatepickerField name="endDate" label="Published Before" />
        </div>

        <div class="mb-3" v-if="selectedFilters.length > 0">
          <label class="form-label fw-bold py-2">Selected Filters</label>
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
        </div>
      </form>
    </template>
  </ListSidebar>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed, ref, watch } from "vue";
import { defineProps } from "vue";
import ListSidebar from "@/components/ListSidebar.vue";
import DatepickerField from "@/components/form/DatepickerField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import { useForm } from "@/composables/form";
import { useCodebaseAPI } from "@/composables/api";

// Define the props
const props = defineProps<{
  programmingLanguages: Record<string, number>;
}>();

const programmingLanguages = Object.entries(props.programmingLanguages)
  .sort(([, countA], [, countB]) => countB - countA) // Sort by count in descending order
  .map(([lang, count]) => ({ value: lang, label: `${lang} (${count})` }));

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
  programmingLanguages: yup.array().of(yup.string()),
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
    ...(values.programmingLanguages.length > 0
      ? values.programmingLanguages.map(lang => ({
          key: `lang_${lang}`,
          label: `Language: ${programmingLanguages.find(l => l.value === lang)?.label || lang}`,
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
    ...(values.tags.length > 0
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
    values.programmingLanguages = values.programmingLanguages.filter(
      lang => `lang_${lang}` !== key
    );
  } else if (key === "startDate") {
    values.startDate = null;
  } else if (key === "endDate") {
    values.endDate = null;
  } else if (key.startsWith("tag_")) {
    const tagName = key.slice(4); // Remove 'tag_' prefix
    values.tags = values.tags.filter(tag => tag.name !== tagName);
  }
  updateFilters();
};

const query = computed(() => {
  const url = new URLSearchParams(window.location.search);
  const searchQuery = url.get("query") ?? "";

  return searchUrl({
    query: searchQuery,
    published_after: values.startDate?.toISOString(),
    published_before: values.endDate?.toISOString(),
    tags: values.tags.map(tag => tag.name),
    peer_review_status: values.peerReviewStatus,
    programming_languages: values.programmingLanguages,
    ordering: values.ordering,
  });
});

const initializeFilters = () => {
  const urlParams = new URLSearchParams(window.location.search);

  values.peerReviewStatus = urlParams.get("peer_review_status") || "";
  values.programmingLanguages = urlParams.getAll("programming_languages");
  values.tags = urlParams.getAll("tags").map(tag => ({ name: tag }));
  values.startDate = urlParams.get("published_after")
    ? new Date(urlParams.get("published_after")!)
    : null;
  values.endDate = urlParams.get("published_before")
    ? new Date(urlParams.get("published_before")!)
    : null;
  values.ordering = urlParams.get("ordering") || "";

  updateFilters();
};

const clearAllFilters = () => {
  values.peerReviewStatus = "";
  values.programmingLanguages = [];
  values.tags = [];
  values.startDate = null;
  values.endDate = null;
  values.ordering = "";

  updateFilters();

  window.location.href = query.value;
};

watch([() => values.startDate, () => values.endDate, () => values.tags], updateFilters);

initializeFilters();

defineExpose({ clearAllFilters });
</script>
