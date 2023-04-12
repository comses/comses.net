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
      <FormLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </div>
    <slot name="help">
      <FormHelp v-if="help" :help="help" :id-for="id" />
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

export interface CheckboxProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
}

const props = withDefaults(defineProps<CheckboxProps>(), {
  help: "",
});

const { id, value, attrs, error } = useField<boolean>(props, "name");
</script>
