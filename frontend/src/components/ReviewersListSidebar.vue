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
  <div class="form-check">
    <input
      type="checkbox"
      id="include-inactive"
      class="form-check-input"
      v-model="includeInactive"
    />
    <FieldLabel label="Include Inactive" id-for="include-inactive" />
  </div>
  <FieldLabel label="Name" id-for="name" />
  <input
    type="text"
    id="name"
    placeholder="Name or Username"
    class="mb-3 form-control"
    v-model="name"
  />
  <label class="form-label">Programming Languages</label>
  <div style="max-height: 300px; overflow-y: scroll">
    <div v-for="language of programmingLanguages" class="form-check">
      <input
        type="checkbox"
        :id="'lang-' + language"
        class="form-check-input"
        :value="language"
        v-model="languages"
      />
      <FieldLabel :label="language" :id-for="'lang-' + language" />
    </div>
  </div>
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
import { defineEmits, ref, watch } from "vue";
import FieldLabel from "./form/FieldLabel.vue";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReviewerEditForm from "@/components/ReviewerEditForm.vue";
import type { ReviewerFilterParams } from "@/types";

const props = withDefaults(defineProps<{ programmingLanguages: string[] }>(), {});

const emit = defineEmits<{
  filter: [ReviewerFilterParams];
  addSuccess: [];
}>();

const addForm = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
const addModal = ref<InstanceType<typeof BootstrapModal> | null>(null);
const includeInactive = ref(false);
const name = ref("");
const languages = ref<string[]>([]);

watch(
  () => ({
    includeInactive: includeInactive.value,
    name: name.value,
    programmingLanguages: languages.value,
  }),
  filters => {
    emit("filter", filters);
  }
);
</script>
