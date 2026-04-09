<template>
  <AccordionStep :is-completed="isConnected" :collapse="collapse">
    <template #title="{ isCompleted }">
      <span v-if="!isCompleted">Connect GitHub Account</span>
      <span v-else-if="githubAccount">
        Signed in as
        <a :href="githubAccount.profileUrl" target="_blank" class="badge bg-dark">
          <i class="fab fa-github me-1"></i>
          {{ githubAccount.username }}
        </a>
      </span>
    </template>

    <template #actions="{ isCompleted }">
      <a
        v-if="isCompleted && installationStatus.connectUrl"
        :href="installationStatus.connectUrl"
        target="_blank"
        class="btn btn-link btn-sm p-0"
      >
        <i class="fas fa-edit"></i>
      </a>
    </template>

    <template #content>
      <div v-if="!githubAccount" class="text-center">
        <div class="mb-3">
          <p class="text-muted">Connect your GitHub account with your CoMSES Net profile</p>
        </div>
        <a
          v-if="installationStatus.connectUrl"
          :href="installationStatus.connectUrl"
          target="_blank"
          class="btn btn-secondary"
          @click="emit('redirected')"
        >
          <i class="fab fa-github me-2"></i>
          Connect GitHub
        </a>
      </div>
    </template>
  </AccordionStep>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { GitHubAppInstallationStatus } from "@/types";
import AccordionStep from "./AccordionStep.vue";

export interface ConnectGitHubStepProps {
  installationStatus: GitHubAppInstallationStatus;
  collapse?: boolean;
}

const props = withDefaults(defineProps<ConnectGitHubStepProps>(), {
  collapse: false,
});

const emit = defineEmits<{ redirected: [] }>();

const githubAccount = computed(() => props.installationStatus.githubAccount);
const isConnected = computed(() => !!githubAccount.value);
</script>
