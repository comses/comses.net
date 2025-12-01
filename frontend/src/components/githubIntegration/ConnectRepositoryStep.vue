<template>
  <AccordionStep :is-completed="!!activeRemote" :collapse="collapse">
    <template #title="{ isCompleted }">
      <span v-if="!isCompleted">Connect Repository</span>
      <span v-else>
        Connected to
        <a :href="activeRemote!.url || '#'" target="_blank" class="badge bg-dark">
          <i class="fab fa-github me-1"></i>
          {{ activeRemote!.owner }}/{{ activeRemote!.repoName }}
        </a>
      </span>
    </template>

    <template #actions="{ isCompleted }">
      <button v-if="isCompleted" class="btn btn-link btn-sm p-0" @click="handleChange">
        <i class="fas fa-edit"></i>
      </button>
    </template>

    <template #content>
      <div class="alert alert-warning py-2 mb-3">
        <small>
          <i class="fas fa-exclamation-triangle me-2"></i>
          Make sure the CoMSES Integration GitHub App has access to the repository you want to
          connect.
          <a v-if="installationUrl" :href="installationUrl" target="_blank"
            >Manage permissions <i class="fas fa-external-link-alt ms-1"></i
          ></a>
        </small>
      </div>
      <p class="text-muted mb-3">
        Enter the <strong>name</strong> of your repository to connect it
      </p>

      <div class="mb-3">
        <label for="repo-url" class="form-label">Repository Name</label>
        <input
          id="repo-url"
          type="text"
          class="form-control"
          placeholder="repository name"
          :value="repoName"
          @input="updateRepoUrl"
        />
      </div>

      <button
        class="btn btn-primary"
        :disabled="!repoName.trim() || isValidating"
        @click="handleConnect"
      >
        {{ isValidating ? "Connecting..." : "Connect Repository" }}
      </button>
    </template>
  </AccordionStep>
</template>

<script setup lang="ts">
import AccordionStep from "./AccordionStep.vue";
import type { CodebaseGitRemote } from "@/types";

export interface ConnectRepositoryStepProps {
  activeRemote: CodebaseGitRemote | null;
  repoName: string;
  installationUrl: string | null;
  isValidating: boolean;
  collapse?: boolean;
}

const props = withDefaults(defineProps<ConnectRepositoryStepProps>(), {
  collapse: false,
});

const emit = defineEmits<{
  connect: [];
  "update:repoName": [value: string];
  change: [];
}>();

const updateRepoUrl = (event: Event) => {
  const target = event.target as HTMLInputElement;
  emit("update:repoName", target.value);
};

const handleConnect = () => {
  if (!props.repoName.trim()) return;
  emit("connect");
};

const handleChange = () => {
  emit("change");
};
</script>
