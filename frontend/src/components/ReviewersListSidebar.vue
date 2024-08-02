<template>
  <form @submit="handleSubmit">
    <CheckboxField name="includeInactive" label="Include Inactive" />
    <button type="submit" class="btn btn-primary mb-2">Filter</button>
  </form>
  <button
    type="button"
    class="btn btn-primary"
    rel="nofollow"
    @click="
      addForm?.resetForm();
      addModal?.show();
    "
  >
    <i class="fas fa-plus-square me-1"></i> Add a Reviewer
  </button>
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
import { computed, defineEmits, ref } from "vue";
import CheckboxField from "./form/CheckboxField.vue";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReviewerEditForm from "@/components/ReviewerEditForm.vue";
import { useForm } from "@/composables/form";
import { ReviewerFilterParams } from "@/types";

const emit = defineEmits<{
  filter: [ReviewerFilterParams];
  addSuccess: [];
}>();

const addForm = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
const addModal = ref<InstanceType<typeof BootstrapModal> | null>(null);

const schema = yup.object<ReviewerFilterParams>({
  includeInactive: yup.boolean().default(false),
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
