<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <VueDatePicker
      v-else
      v-model="value"
      format="yyyy-MM-dd"
      :id="id"
      v-bind="attrs"
      :placeholder="placeholder"
      :class="{ 'is-invalid': error }"
      :input-class-name="error ? 'is-invalid' : ''"
      menu-class-name="custom-dp__menu"
      :hide-input-icon="true"
      :auto-apply="true"
      :enable-time-picker="false"
      :min-date="minDate"
    ></VueDatePicker>
    <slot name="help">
      <FormHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FormError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { inject } from "vue";
import VueDatePicker from "@vuepic/vue-datepicker";
import { useField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";

export interface DatePickerProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  minDate?: Date;
}

const props = defineProps<DatePickerProps>();

const { id, value, attrs, error } = useField<Date>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
