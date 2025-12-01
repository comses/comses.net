<template>
  <AccordionStep :is-completed="isCompleted" :collapse="collapse">
    <template #title="{ isCompleted }">
      <span v-if="!isCompleted">Select Sync Type</span>
      <span v-else>
        {{
          selectedSyncType === "existing"
            ? "Syncing with existing repository"
            : "Syncing with new repository"
        }}
      </span>
    </template>
    <template #content>
      <div v-if="!isNewRepoPending && !selectedSyncType">
        <div class="row g-4">
          <div class="col-12 col-md-6">
            <div class="text-center mb-3">
              <button class="btn btn-primary w-100" @click="emit('choice', 'existing')">
                <i class="fas fa-code-branch me-2"></i>
                I have an existing GitHub repository
              </button>
            </div>
            <div class="text-muted small">
              Connect to a repository you already have on GitHub, allowing you to
              <b>import</b> releases made there to the CoMSES Model Library.
            </div>
          </div>

          <div class="col-12 col-md-6">
            <div class="text-center mb-3">
              <button class="btn btn-primary w-100" @click="isNewRepoPending = true">
                <i class="fas fa-plus me-2"></i>
                Build a new repository for my model
              </button>
            </div>
            <div class="text-muted small">
              You will create a new GitHub repository, then a git repo will be automatically
              constructed from your releases published here, which you can
              <b>push</b>. This is an easy way to start using GitHub and you'll be able to
              <b>import</b> any future releases created there.
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="isNewRepoPending">
        <div class="d-flex justify-content-start mb-3">
          <button class="btn btn-link p-0 text-decoration-none" @click="isNewRepoPending = false">
            <i class="fas fa-arrow-left me-2"></i>
            Back
          </button>
        </div>

        <p class="text-muted small mb-3">
          You'll need to create an empty repository on GitHub first. After you connect it, the
          history will be built and you'll be able to push it.
        </p>

        <div class="alert alert-warning py-2 mb-3">
          <small>
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Important:</strong> Do NOT initialize the repository with README, .gitignore, or
            license files.
          </small>
        </div>

        <div class="row g-2">
          <div class="col-12 col-md-6">
            <a :href="newRepositoryUrl" target="_blank" class="btn btn-secondary w-100">
              <i class="fas fa-external-link-alt me-2"></i>
              Create New Repository
            </a>
          </div>
          <div class="col-12 col-md-6">
            <button class="btn btn-primary w-100" @click="emit('choice', 'new')">
              <i class="fas fa-arrow-right me-2"></i>
              Continue
            </button>
          </div>
        </div>
      </div>
    </template>
    <template #actions="{ isCompleted }">
      <button v-if="isCompleted" class="btn btn-link btn-sm p-0" @click="emit('reset')">
        <i class="fas fa-undo"></i>
      </button>
    </template>
  </AccordionStep>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import AccordionStep from "./AccordionStep.vue";

export interface SelectSyncTypeStepProps {
  selectedSyncType?: "existing" | "new" | null;
  collapse?: boolean;
  newRepositoryUrl: string;
}

const props = withDefaults(defineProps<SelectSyncTypeStepProps>(), {
  selectedSyncType: null,
  collapse: false,
});

const emit = defineEmits<{
  choice: [syncType: "existing" | "new"];
  reset: [];
}>();

const isCompleted = computed(() => props.selectedSyncType !== null);
const isNewRepoPending = ref(false);
</script>
