<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="indicateRequired" />
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
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import { inject } from "vue";

export interface TextInputProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  indicateRequired?: boolean;
  rows?: number;
}

const props = withDefaults(defineProps<TextInputProps>(), {
  rows: 10,
});

const { id, value, attrs, error } = useField<string>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
