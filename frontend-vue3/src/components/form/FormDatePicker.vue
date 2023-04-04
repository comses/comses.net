<template>
  <div>
    <slot name="label">
      <FormLabel :label="label" :id-for="id" :required="required"></FormLabel>
    </slot>
    <VueDatePicker
      v-model="(value as Date)"
      :id="id"
      v-bind="attrs"
      :class="{ 'is-invalid': error }"
      :auto-apply="true"
      :enable-time-picker="false"
    ></VueDatePicker>
    <FormHelpErrors :help="help" :id-for="id" :error="error"></FormHelpErrors>
  </div>
</template>

<script setup lang="ts">
import VueDatePicker from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css" // TODO: use scss in global styles
                                             // https://vue3datepicker.com/props/look-and-feel/
import { useFormField } from "@/composables/formfield";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelpErrors from "@/components/form/FormHelpErrors.vue";

export type SelectOptions = { value: any; label: string }[];

export interface TextInputProps {
  name: string;
  label: string;
  help?: string;
  required?: boolean;
}
const props = defineProps<TextInputProps>();
const { id, value, attrs, error } = useFormField(props, "name");
</script>
