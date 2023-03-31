<template>
  <div>
    <slot name="label">
      <FormLabel :label="label" :id-for="name" :required="required"></FormLabel>
    </slot>
    <select
      v-model="value"
      :id="name"
      v-bind="attrs"
      :class="{ 'form-select': true, 'is-invalid': error }"
    >
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <FormHelpErrors :help="help" :id-for="name" :error="error"></FormHelpErrors>
  </div>
</template>

<script setup lang="ts">
import { toRef } from "vue";
import { useField } from "@vorms/core";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelpErrors from "@/components/form/FormHelpErrors.vue";

export type SelectOptions = { value: any; label: string }[];

export interface TextInputProps {
  name: string;
  label: string;
  help?: string;
  required?: boolean;
  options: SelectOptions;
}

const props = defineProps<TextInputProps>();

const nameRef = toRef(props, "name");
const { value, attrs, error } = useField(nameRef);
</script>
