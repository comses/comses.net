<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <select
      v-else
      v-model="value"
      :id="id"
      v-bind="attrs"
      :class="{ 'form-select': true, 'is-invalid': error }"
      @change="attrs.onInput()"
    >
      <option
        v-for="option in options"
        :key="option.value"
        :value="option.value"
        :selected="option.value === value"
      >
        {{ option.label }}
      </option>
    </select>
    <slot name="help">
      <FieldHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FieldError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { useField } from "@/composables/form";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import { inject } from "vue";

export interface SelectFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  options: { value: any; label: string }[];
}

const props = defineProps<SelectFieldProps>();

const { id, value, attrs, error } = useField<any>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
