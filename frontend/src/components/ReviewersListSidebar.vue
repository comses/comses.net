<template>
  <button
    type="button"
    class="btn btn-primary mb-3"
    rel="nofollow"
    @click="
      addForm?.resetForm();
      addModal?.show();
    "
  >
    <i class="fas fa-plus-square me-1"></i> Add a Reviewer
  </button>
  <form @submit="handleSubmit">
    <CheckboxField name="includeInactive" label="Include Inactive" />
    <TextField class="mb-3" name="name" label="Name" placeholder="Name or Username" />
    <MultiSelectField
      class="mb-3"
      name="programmingLanguages"
      label="Programming Languages"
      multiple
      :options="programmingLanguages"
      :custom-label="option => option"
    />
    <button type="submit" class="btn btn-primary">Filter</button>
  </form>
  <BootstrapModal id="add-modal" title="Add Reviewer" ref="addModal" size="lg" centered>
    <template #content>
      <ReviewerEditForm
        id="add-reviewer-form"
        :is-edit="false"
        ref="addForm"
        @success="
          () => {
            emit('addSuccess');
            addModal?.hide();
          }
        "
      />
    </template>
  </BootstrapModal>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { defineEmits, ref } from "vue";
import CheckboxField from "./form/CheckboxField.vue";
import TextField from "./form/TextField.vue";
import MultiSelectField from "./form/MultiSelectField.vue";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReviewerEditForm from "@/components/ReviewerEditForm.vue";
import { useForm } from "@/composables/form";
import type { ReviewerFilterParams } from "@/types";

const props = withDefaults(defineProps<{ programmingLanguages: string[] }>(), {});

const emit = defineEmits<{
  filter: [ReviewerFilterParams];
  addSuccess: [];
}>();

const addForm = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
const addModal = ref<InstanceType<typeof BootstrapModal> | null>(null);

const schema = yup.object<ReviewerFilterParams>({
  includeInactive: yup.boolean().default(false),
  name: yup.string().default(""),
  programmingLanguages: yup.array().of(yup.string()).default([]),
});

const { handleSubmit, values } = useForm<ReviewerFilterParams>({
  schema,
  initialValues: {
    includeInactive: false,
  },
  onSubmit: () => {
    emit("filter", values);
  },
});
</script>
