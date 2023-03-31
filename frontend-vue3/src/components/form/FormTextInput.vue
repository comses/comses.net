<template>
  <div>
    <slot name="label">
      <FormLabel :label="label" :id-for="id" :required="required"></FormLabel>
    </slot>
    <input
      v-model="value"
      :type="type"
      :id="id"
      v-bind="attrs"
      :class="{ 'form-control': true, 'is-invalid': error }"
    />
    <FormHelpErrors :help="help" :id-for="id" :error="error"></FormHelpErrors>
  </div>
</template>

<script setup lang="ts">
import { useFormField } from "@/composables/formfield";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelpErrors from "@/components/form/FormHelpErrors.vue";

export interface TextInputProps {
  name: string;
  label: string;
  help?: string;
  required?: boolean;
  type?: "text" | "email" | "password" | "number" | "tel" | "url" | "search";
}

const props = withDefaults(defineProps<TextInputProps>(), {
  type: "text",
});

const { id, value, attrs, error } = useFormField(props, "name");
</script>
