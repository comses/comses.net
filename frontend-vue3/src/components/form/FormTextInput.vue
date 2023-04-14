<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="indicateRequired" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <input
      v-else
      v-model="value"
      :type="type"
      :id="id"
      v-bind="attrs"
      :class="{ 'form-control': true, 'is-invalid': error }"
    />
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
import { useField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";

export interface TextInputProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  indicateRequired?: boolean;
  // generally it is better to leave type="text" for url/email/etc. inputs so that the browser
  // does not perform any validation before the form/yup does leading to visual inconsistency
  type?: "text" | "email" | "password" | "number" | "tel" | "url" | "search";
}

const props = withDefaults(defineProps<TextInputProps>(), {
  type: "text",
});

const { id, value, attrs, error } = useField<string>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
