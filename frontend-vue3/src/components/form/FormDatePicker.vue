<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <VueDatePicker
      v-model="value"
      :model-type="string ? 'yyyy-MM-dd' : undefined"
      format="yyyy-MM-dd"
      :id="id"
      v-bind="attrs"
      :placeholder="placeholder"
      :class="{ 'is-invalid': error }"
      input-class-name="custom-dp__input"
      menu-class-name="custom-dp__menu"
      :hide-input-icon="true"
      :auto-apply="true"
      :enable-time-picker="false"
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
import VueDatePicker from "@vuepic/vue-datepicker";
import { useField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";

export interface DatePickerProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  string?: boolean; // whether to use string or date for the model value
}

const props = withDefaults(defineProps<DatePickerProps>(), {
  string: false,
});

const { id, value, attrs, error } = useField<Date | string>(props, "name");
</script>
