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
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </div>
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
import type { BaseFieldProps } from "@/types";

const props = withDefaults(defineProps<BaseFieldProps>(), {
  help: "",
});

const { id, value, attrs, error } = useField<boolean>(props, "name");
</script>
