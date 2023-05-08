<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <VueMultiSelect
      v-else
      v-model="value"
      :id="id"
      v-bind="attrs"
      :multiple="false"
      track-by="name"
      label="name"
      :placeholder="placeholder"
      :allow-empty="true"
      :options="matchingOrgs"
      :disabled="disabled"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :close-on-select="true"
      :options-limit="10"
      @search-change="fetchMatchingOrgs"
      @select="handleSelect"
      :class="{ 'is-invalid': error }"
    >
      <template #clear v-if="value">
        <div class="multiselect__clear">
          <span @mousedown.prevent.stop="value = null">&times;</span>
        </div>
      </template>
      <template #caret="{ toggle }">
        <div :class="{ 'multiselect__search-toggle': true, 'd-none': !!value }">
          <i class="fas fa-search" @mousedown.prevent.stop="toggle" />
        </div>
      </template>
      <template #option="{ option }">
        <div>
          <span>{{ option.name }}</span>
          <br />
          <span class="option--desc">
            <small>{{ option.url }}</small>
          </span>
        </div>
      </template>
      <template #noOptions>No results found.</template>
      <template #noResult v-if="serverErrors.length > 0">
        Unable to reach the <a href="https://ror.org/">Research Organization Registry</a>. Check
        your connection or try again later.
        <div class="mt-2 text-danger">
          <small>{{ serverErrors.join(", ") }}</small>
        </div>
      </template>
    </VueMultiSelect>
    <slot name="help">
      <FieldHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FieldError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { ref, inject } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useDebounceFn } from "@vueuse/core";
import { useField } from "@/composables/form";
import { useRORAPI } from "@/composables/api/ror";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import type { Organization } from "@/types";

interface ResearchOrgFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  clearOnSelect?: boolean;
}

const props = withDefaults(defineProps<ResearchOrgFieldProps>(), {
  placeholder: "Type to find your organization",
  disabled: false,
  clearOnSelect: false,
});
const emit = defineEmits(["select"]);

const { id, value, attrs, error } = useField<Organization | null>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);

const matchingOrgs = ref<Organization[]>([]);
const isLoading = ref(false);

const { serverErrors, search } = useRORAPI();

function handleSelect(event: Event) {
  emit("select", event);
  if (props.clearOnSelect) {
    value.value = null;
  }
}

const fetchMatchingOrgs = useDebounceFn(async (query: string) => {
  if (query) {
    isLoading.value = true;
    try {
      matchingOrgs.value = await search(query);
    } catch (e) {
      // no-op
    } finally {
      isLoading.value = false;
    }
  }
}, 600);
</script>
