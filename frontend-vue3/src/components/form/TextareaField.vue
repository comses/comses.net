<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" :rows="rows" />
    <textarea
      v-else
      v-model="value"
      :rows="rows"
      :id="id"
      v-bind="attrs"
      :class="{ 'form-control': true, 'is-invalid': error }"
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

interface TextareaFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  rows?: number;
}

const props = withDefaults(defineProps<TextareaFieldProps>(), {
  rows: 10,
});

const { id, value, attrs, error } = useField<string>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
