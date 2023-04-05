<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <input
      v-model="value"
      :type="type"
      :id="id"
      v-bind="attrs"
      :class="{ 'form-control': true, 'is-invalid': error }"
    />
    <slot name="help">
      <FormHelp v-if="help" :help="help" :id-for="id" :error="error" />
    </slot>
    <slot name="error">
      <FormError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { useField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";

export interface TextInputProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  type?: "text" | "email" | "password" | "number" | "tel" | "url" | "search";
}

const props = withDefaults(defineProps<TextInputProps>(), {
  type: "text",
});

const { id, value, attrs, error } = useField(props, "name");
</script>
