<template>
  <div>
    <div class="form-check">
      <input
        v-model="value"
        type="checkbox"
        :id="name"
        v-bind="attrs"
        :class="{ 'form-check-input': true, 'is-invalid': error }"
      />
      <FormLabel :label="label" :id-for="name" :required="required"></FormLabel>
    </div>
    <FormHelpErrors class="mt-n2" :help="help" :id-for="name" :error="error"></FormHelpErrors>
  </div>
</template>

<script setup lang="ts">
import { toRef } from "vue";
import { useField } from "@vorms/core";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelpErrors from "@/components/form/FormHelpErrors.vue";

export interface CheckboxProps {
  name: string;
  label: string;
  help?: string;
  required?: boolean;
}

const props = withDefaults(defineProps<CheckboxProps>(), {
  help: "",
});

const nameRef = toRef(props, "name");
const { value, attrs, error } = useField(nameRef);
</script>
