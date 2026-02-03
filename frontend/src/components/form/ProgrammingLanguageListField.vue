<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <div class="form-check-inline ms-3">
      <label class="form-check-label" :for="`${id}-custom-input-check`">
        <input
          type="checkbox"
          class="form-check-input me-1"
          v-model="showCustomInput"
          :id="`${id}-custom-input-check`"
          :disabled="disabled"
        />
        <small class="text-muted">Enter manually</small>
      </label>
    </div>
    <FormPlaceholder v-if="showPlaceholder" />
    <span v-else-if="showCustomInput">
      <div class="input-group">
        <input
          v-model="languageCustomName"
          :id="id"
          :class="['form-control', { 'is-invalid': localErrors.name }]"
          placeholder="Enter the name of the programming language"
          @input="localErrors.name = ''"
          @keydown.enter.prevent="createCustom"
        />
        <button
          type="button"
          v-if="languageCustomName"
          class="btn btn-outline-secondary"
          @click="createCustom"
        >
          <small>Press enter to add</small>
        </button>
      </div>
      <FieldError
        v-if="localErrors.name || localErrors.url"
        :error="localErrorMessage"
        :id-for="id"
      />
    </span>
    <VueMultiSelect
      v-else
      :id="id"
      v-bind="attrs"
      track-by="name"
      label="name"
      :placeholder="isLoadingOptions ? 'Loading programming languages...' : placeholder"
      :allow-empty="true"
      :options="programmingLanguageOptions"
      :disabled="disabled || isLoadingOptions"
      @select="create"
      :class="{ 'is-invalid': error }"
    >
    </VueMultiSelect>
    <Sortable :list="languages" :item-key="item => item" @end="sort($event)">
      <template #item="{ element, index }">
        <div :key="element" class="my-1 input-group">
          <input
            :value="element.programmingLanguage.name"
            class="form-control w-25"
            readonly
            :disabled="disabled"
          />
          <input
            v-model="element.version"
            placeholder="Language version (e.g. 3.12)"
            class="form-control w-50"
          />
          <button
            type="button"
            class="btn btn-delete-item"
            tabindex="-1"
            @click.once="remove(index)"
            :disabled="disabled"
          >
            &times;
          </button>
        </div>
      </template>
    </Sortable>
    <slot name="help">
      <FieldHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FieldError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { inject, ref, onMounted, reactive, computed } from "vue";
import { Sortable } from "sortablejs-vue3";
import type { SortableEvent } from "sortablejs";
import VueMultiSelect from "vue-multiselect";
import { useField } from "@/composables/form";
import { useProgrammingLanguageAPI } from "@/composables/api/programmingLanguage";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import type { ProgrammingLanguage, ReleaseLanguage } from "@/types";

const { list: fetchProgrammingLanguages } = useProgrammingLanguageAPI();

let programmingLanguageOptions: ProgrammingLanguage[] = [];
const isLoadingOptions = ref(false);

async function loadProgrammingLanguages() {
  try {
    isLoadingOptions.value = true;
    const response = await fetchProgrammingLanguages();
    programmingLanguageOptions = response.data;
  } catch (error) {
    console.error("Failed to fetch programming languages:", error);
  } finally {
    isLoadingOptions.value = false;
  }
}

export interface ProgrammingLanguageListFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}

const props = defineProps<ProgrammingLanguageListFieldProps>();
onMounted(() => {
  if (!languages.value) {
    // force initialize to empty array
    languages.value = [];
  }
  // Load programming languages from API
  loadProgrammingLanguages();
});

const showCustomInput = ref(false);
const languageCustomName = ref("");
const localErrors = reactive({ name: "", url: "" });

const localErrorMessage = computed(() => {
  return `${localErrors.name}
          ${localErrors.name && localErrors.url ? "and " : ""}
          ${localErrors.url}`;
});

function createCustom() {
  const customLang: ProgrammingLanguage = {
    name: languageCustomName.value,
  };
  if (
    !languages.value.some(
      e => e.programmingLanguage.name.toLowerCase() === customLang.name.toLowerCase()
    )
  ) {
    create(customLang);
    languageCustomName.value = "";
  }
}

function create(language: ProgrammingLanguage) {
  const releaseLanguage: ReleaseLanguage = {
    programmingLanguage: language,
    version: "",
  };
  if (!languages.value) languages.value = [];
  languages.value.push(releaseLanguage);
}

function remove(index: number) {
  languages.value.splice(index, 1);
}

function sort(event: SortableEvent) {
  const { newIndex, oldIndex } = event;
  if (newIndex !== undefined && oldIndex !== undefined) {
    const item = languages.value.splice(oldIndex, 1)[0];
    languages.value.splice(newIndex, 0, item);
  }
}

const { id, value: languages, attrs, error } = useField<ReleaseLanguage[]>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
