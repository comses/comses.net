<template>
  <div>
    <a :href="remote.url" target="_blank">
      <i class="fab fa-github"></i>
      {{ remote.owner }}/{{ remote.repoName }}
    </a>
  </div>
  <div>
    <div v-if="!remote.isPreexisting" class="form-check form-switch">
      <input
        class="form-check-input"
        type="checkbox"
        id="flexSwitchCheckDefault"
        :checked="remote.shouldPush"
        @change="confirmToggle('shouldPush', remote.shouldPush, $event)"
      />
      <label class="form-check-label" for="flexSwitchCheckDefault">Pushing</label>
      <div>
        <small class="form-text text-muted"
          ><small><i class="fas fa-code-branch"></i> to GitHub</small></small
        >
      </div>
    </div>
    <div v-if="remote.isUserRepo" class="form-check form-switch">
      <input
        class="form-check-input"
        type="checkbox"
        id="flexSwitchCheckDefault1"
        :checked="remote.shouldArchive"
        @change="confirmToggle('shouldArchive', remote.shouldArchive, $event)"
      />
      <label class="form-check-label" for="flexSwitchCheckDefault1">Archiving</label>
      <div>
        <small class="form-text text-muted"
          ><small><i class="fas fa-archive"></i> from GitHub</small></small
        >
      </div>
    </div>

    <BootstrapModal
      :id="`confirmModal-${remote.id}`"
      title="Confirm choice"
      ref="confirmModal"
      centered
    >
      <template #body>
        Are you sure you want to {{ pendingToggleValue ? "enable" : "disable" }}
        {{ toggleField === "shouldPush" ? "pushing to " : "archiving from " }}
        <a :href="remote.url" target="_blank">{{ remote.owner }}/{{ remote.repoName }}</a
        >?
        <FormAlert v-if="serverErrors" :validation-errors="[]" :server-errors="serverErrors" />
      </template>
      <template #footer>
        <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-primary" @click="applyToggle">Confirm</button>
      </template>
    </BootstrapModal>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import Modal from "bootstrap/js/dist/modal";
import type { CodebaseGitRemote } from "@/types";
import { useGitRemotesAPI } from "@/composables/api/git";
import FormAlert from "@/components/form/FormAlert.vue";
import BootstrapModal from "@/components/BootstrapModal.vue";

const props = defineProps<{
  codebaseIdentifier: string;
  remote: CodebaseGitRemote;
}>();

const emit = defineEmits<{
  changed: [CodebaseGitRemote];
}>();

const { serverErrors, update } = useGitRemotesAPI(props.codebaseIdentifier);

const toggleField = ref("");
const pendingToggleValue = ref(false);
const confirmModal = ref<Modal>();

const confirmToggle = (field: string, currentValue: boolean, event: any) => {
  toggleField.value = field;
  pendingToggleValue.value = !currentValue;
  event.target.checked = currentValue;
  event.preventDefault();
  serverErrors.value = [];
  confirmModal.value?.show();
};

const applyToggle = async () => {
  await update(
    props.remote.id,
    { [toggleField.value]: pendingToggleValue.value },
    {
      onSuccess: () => {
        confirmModal.value?.hide();
        emit("changed", props.remote);
      },
    }
  );
};
</script>
