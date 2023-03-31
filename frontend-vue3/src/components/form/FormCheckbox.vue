<template>
  <div>
    <div class="form-check">
      <input
        v-model="value"
        type="checkbox"
        :id="id"
        v-bind="attrs"
        :class="{ 'form-check-input': true, 'is-invalid': error }"
      />
      <FormLabel :label="label" :id-for="id" :required="required"></FormLabel>
    </div>
    <FormHelpErrors class="mt-n2" :help="help" :id-for="id" :error="error"></FormHelpErrors>
  </div>
</template>

<script setup lang="ts">
import { useFormField } from "@/composables/formfield";
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

const { id, value, attrs, error } = useFormField(props, "name");
</script>
