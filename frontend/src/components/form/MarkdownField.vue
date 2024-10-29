<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" :rows="rows" />
    <textarea
      v-else
      v-model="text"
      :rows="rows"
      :id="id"
      v-bind="attrs"
      :class="{ 'form-control': true, 'is-invalid': error }"
    />
    <a
      class="fab fa-markdown text-gray me-2"
      title="Markdown formatting is supported"
      href="https://www.markdownguide.org/basic-syntax/"
      target="_blank"
      tabindex="-1"
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
import { useField } from "@/composables/form";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import { inject } from "vue";

export interface MarkdownFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  rows?: number;
}

const props = withDefaults(defineProps<MarkdownFieldProps>(), {
  rows: 10,
});

const { id, value: text, attrs, error } = useField<string>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
