<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <input
      v-else
      v-model="text"
      :type="type"
      :id="id"
      :placeholder="placeholder"
      v-bind="attrs"
      :class="{ 'form-control': true, 'is-invalid': error }"
      :disabled="disabled"
    />
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
import { useField } from "@/composables/form";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";

export interface TextFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  // generally it is better to leave type="text" for url/email/etc. inputs so that the browser
  // does not perform any validation before the form/yup does leading to visual inconsistency
  type?: "text" | "email" | "password" | "number" | "tel" | "url" | "search";
}

const props = withDefaults(defineProps<TextFieldProps>(), {
  type: "text",
});

const { id, value: text, attrs, error } = useField<string>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
