<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <VueDatePicker
      v-model="value"
      model-type="yyyy-MM-dd"
      :id="id"
      v-bind="attrs"
      :class="{ 'is-invalid': error }"
      :auto-apply="true"
      :enable-time-picker="false"
    ></VueDatePicker>
    <slot name="help">
      <FormHelp v-if="help" :help="help" :id-for="id" :error="error" />
    </slot>
    <slot name="error">
      <FormError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import VueDatePicker from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css"; // TODO: use scss in global styles
// https://vue3datepicker.com/props/look-and-feel/
import { useField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";

export type SelectOptions = { value: any; label: string }[];

export interface TextInputProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
}

const props = defineProps<TextInputProps>();

const { id, value, attrs, error } = useField<string>(props, "name");
</script>
