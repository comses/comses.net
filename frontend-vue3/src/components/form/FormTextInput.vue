<template>
  <div>
    <slot name="label">
      <FormLabel :label="label" :id-for="name" :required="required"></FormLabel>
    </slot>
    <input
      v-model="value"
      :type="type"
      :id="name"
      v-bind="attrs"
      :class="{ 'form-control': true, 'is-invalid': error }"
    />
    <FormHelpErrors :help="help" :id-for="name" :error="error"></FormHelpErrors>
  </div>
</template>

<script setup lang="ts">
import { toRef } from "vue";
import { useField } from "@vorms/core";
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

const nameRef = toRef(props, "name");
const { value, attrs, error } = useField(nameRef);
</script>
