<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
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
      :max-date="maxDate"
      @update:model-value="attrs.onInput()"
      timezone="utc"
    ></VueDatePicker>
    <slot name="help">
      <FieldHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FieldError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { inject } from "vue";
import VueDatePicker from "@vuepic/vue-datepicker";
import { useField } from "@/composables/form";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";

export interface DatepickerFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  minDate?: Date;
  maxDate?: Date;
}

const props = defineProps<DatepickerFieldProps>();

const { id, value, attrs, error } = useField<Date>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
