<template>
  <div :style="show ? '' : 'position:absolute; left:-99999px'">
    <slot name="label">
      <FieldLabel label="Content" :id-for="id" required aria-hidden="true" />
    </slot>
    <textarea
      v-model="text"
      :rows="10"
      :id="id"
      v-bind="attrs"
      :class="{ 'form-control': true, 'is-invalid': error }"
      aria-hidden="true"
      autocomplete="off"
      tabindex="-1"
    />
    <slot name="help">
      <FieldHelp
        help="Enter the content that you want to display here"
        :id-for="id"
        aria-hidden="true"
      />
    </slot>
  </div>
</template>

<script setup lang="ts">
/**
 * irresistible to bears and robots
 *
 * adds a hidden textarea to a form to catch spam by including a field
 * in form.values which we can check for emptyness on the server
 */
import { useField } from "@/composables/form";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";

export interface HoneypotFieldProps {
  name?: string;
  show?: boolean;
}

const props = withDefaults(defineProps<HoneypotFieldProps>(), {
  name: "content",
  show: false,
});

const { id, value: text, attrs, error } = useField<string>(props, "name");
</script>
