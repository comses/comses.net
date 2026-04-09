<template>
  <AccordionStep :is-completed="isInstalled" :collapse="collapse">
    <template #title="{ isCompleted }">
      <span v-if="!isCompleted">Install CoMSES Integration GitHub App</span>
      <span v-else>CoMSES Integration GitHub App installed</span>
    </template>

    <template #actions="{ isCompleted }">
      <a
        v-if="isCompleted && installationStatus.installationUrl"
        :href="installationStatus.installationUrl"
        target="_blank"
        class="btn btn-link btn-sm p-0"
      >
        <i class="fas fa-cog"></i>
      </a>
    </template>

    <template #content>
      <div v-if="!isInstalled" class="text-center">
        <div class="mb-3">
          <p class="text-muted">
            This gives our service read and write access to repositories. Make sure to select the
            individual repository(s) you want to connect, or allow access to all repositories (not
            recommended).
          </p>
        </div>
        <div class="d-flex flex-column align-items-center gap-2">
          <a
            :href="installationStatus.installationUrl || ''"
            target="_blank"
            class="btn btn-secondary"
            @click="emit('redirected')"
          >
            <i class="fas fa-download me-2"></i>
            Install App
          </a>
          <small class="text-muted">
            Installed but not recognized? Try refreshing the page or
            <a :href="installationStatus.installationUrl || ''" target="_blank">
              uninstalling and reinstalling the app </a
            >.
          </small>
        </div>
      </div>
    </template>
  </AccordionStep>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { GitHubAppInstallationStatus } from "@/types";
import AccordionStep from "./AccordionStep.vue";

export interface InstallGitHubAppStepProps {
  hasExistingRepo: boolean | null;
  installationStatus: GitHubAppInstallationStatus;
  collapse?: boolean;
}

const props = withDefaults(defineProps<InstallGitHubAppStepProps>(), {
  collapse: false,
});

const emit = defineEmits<{
  redirected: [];
}>();

const isInstalled = computed(() => !!props.installationStatus.githubAccount?.installationId);
</script>
