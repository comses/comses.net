<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <VueMultiSelect
      v-else
      v-model="value"
      :id="id"
      v-bind="attrs"
      :multiple="multiple"
      :track-by="multiple ? undefined : trackBy"
      :label="labelWith"
      :placeholder="placeholder"
      :options="options"
      :hide-selected="false"
      :searchable="true"
      @select="attrs.onInput()"
      :close-on-select="!multiple"
      :custom-label="customLabel"
      :class="{ 'is-invalid': error }"
    >
      <template #clear v-if="multiple && value?.length">
        <div class="multiselect__clear">
          <span @mousedown.prevent.stop="value = []">&times;</span>
        </div>
      </template>
      <template #option="{ option }">
        <slot name="option" :option="option" v-if="!customLabel">
          {{ option[labelWith] }}
        </slot>
      </template>
      <template #caret>
        <div :class="{ multiselect__select: true, 'd-none': value?.length }"></div>
      </template>
    </VueMultiSelect>
    <slot name="help">
      <FieldHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FieldError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { inject } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useField } from "@/composables/form";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";

export interface MultiSelectFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  multiple?: boolean;
  trackBy?: string;
  labelWith?: string;
  customLabel?: (option: any) => void;
  options: any[];
}

const props = withDefaults(defineProps<MultiSelectFieldProps>(), {
  multiple: false,
  trackBy: "value",
  labelWith: "label",
});

const { id, value, attrs, error } = useField<string | any[]>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
