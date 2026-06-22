<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="candidateDoiId" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <div v-else>
      <div class="input-group mb-2">
        <input
          v-model="candidateDoi"
          v-bind="attrs"
          :id="candidateDoiId"
          :class="['form-control', { 'is-invalid': localErrors.doi }]"
          :placeholder="placeholder"
          @input="localErrors.doi = ''"
          @keydown.enter.prevent="create"
        />
        <button type="button" v-if="candidateDoi" class="btn btn-outline-secondary" @click="create">
          <small>Press enter to add</small>
        </button>
      </div>
      <FieldError v-if="localErrors.doi" :error="localErrors.doi" :id-for="candidateDoiId" />
      <Sortable :list="publications" :item-key="item => item.doi" @end="sort($event)">
        <template #item="{ element, index }">
          <div :key="`${element.doi}-${index}`" class="my-1 input-group align-items-stretch">
            <span class="input-group-text bg-white text-gray" title="Drag entries to sort">
              <i class="fas fa-sort" />
            </span>
            <input :value="element.doi" class="form-control" readonly />
            <span class="input-group-text bg-white">
              <label class="form-check-label mb-0">
                <input
                  type="checkbox"
                  class="form-check-input me-1"
                  v-model="element.includeInCitation"
                />
                <small>Cite with main citation</small>
              </label>
            </span>
            <button
              type="button"
              class="btn btn-delete-item"
              tabindex="-1"
              @click.once="remove(index)"
            >
              &times;
            </button>
          </div>
        </template>
      </Sortable>
    </div>
    <slot name="help">
      <FieldHelp v-if="help" :help="help" :id-for="candidateDoiId" />
    </slot>
    <slot name="error">
      <FieldError v-if="error" :error="error" :id-for="candidateDoiId" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, reactive, ref, useAttrs } from "vue";
import { Sortable } from "sortablejs-vue3";
import type { SortableEvent } from "sortablejs";
import { useField } from "@/composables/form";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import type { AssociatedPublication } from "@/types";

export interface AssociatedPublicationListFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
}

const DOI_PATTERN = /^(?:https?:\/\/(?:dx\.)?doi\.org\/)?10\.\d{4,9}\/[-._;()/:A-Z0-9]+$/i;

const props = defineProps<AssociatedPublicationListFieldProps>();
const attrs = useAttrs();

const showPlaceholder = inject("showPlaceholder", false);
const candidateDoi = ref("");
const localErrors = reactive({ doi: "" });

const { id, value: publications, error } = useField<AssociatedPublication[]>(props, "name");
const candidateDoiId = computed(() => `${id}-candidate-doi`);

onMounted(() => {
  if (!publications.value) {
    publications.value = [];
  }
});

function normalizeDoiLink(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  if (trimmed.toLowerCase().startsWith("doi:")) {
    return `https://doi.org/${trimmed.slice(4).trim()}`;
  }
  if (trimmed.toLowerCase().startsWith("http://") || trimmed.toLowerCase().startsWith("https://")) {
    if (trimmed.match(/^https?:\/\/(?:dx\.)?doi\.org\//i)) {
      return trimmed.replace(/^http:\/\//i, "https://");
    }
    return trimmed;
  }
  return `https://doi.org/${trimmed}`;
}

function validateDoi(value: string) {
  const normalized = normalizeDoiLink(value);
  if (!normalized) {
    localErrors.doi = "Please enter a DOI or DOI link.";
    return null;
  }
  const doi = normalized.replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "");
  if (!DOI_PATTERN.test(doi)) {
    localErrors.doi = "Please enter a valid DOI or doi.org link.";
    return null;
  }
  return `https://doi.org/${doi}`;
}

function create() {
  const doi = validateDoi(candidateDoi.value);
  if (!doi) {
    return;
  }
  if (!publications.value) {
    publications.value = [];
  }
  if (publications.value.some(publication => publication.doi === doi)) {
    localErrors.doi = "This DOI is already listed.";
    return;
  }
  publications.value.push({
    doi,
    includeInCitation: true,
  });
  candidateDoi.value = "";
  localErrors.doi = "";
}

function remove(index: number) {
  publications.value.splice(index, 1);
}

function sort(event: SortableEvent) {
  const { newIndex, oldIndex } = event;
  if (newIndex !== undefined && oldIndex !== undefined) {
    const item = publications.value.splice(oldIndex, 1)[0];
    publications.value.splice(newIndex, 0, item);
  }
}
</script>
