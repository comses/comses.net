<template>
  <div class="d-flex align-items-center justify-content-between">
    <div class="d-flex flex-column align-items-start flex-grow-1 me-3">
      <a :href="remote.url" target="_blank">
        <i class="fab fa-github"></i>
        {{ remote.owner }}/{{ remote.repoName }}
      </a>
      <button class="btn btn-sm btn-link text-muted p-0" @click="showLog = !showLog">
        <small>
          <i v-if="showLog" class="fas fa-chevron-up"></i>
          <i v-else class="fas fa-chevron-down"></i>
          Sync log
        </small>
      </button>
    </div>
    <div class="d-flex flex-row flex-shrink-0 gap-3">
      <div v-if="!remote.isPreexisting" class="form-check form-switch me-3">
        <input
          class="form-check-input"
          type="checkbox"
          id="flexSwitchCheckDefault"
          :checked="remote.shouldPush"
          @change="confirmToggle('shouldPush', remote.shouldPush, $event)"
        />
        <label class="form-check-label" for="flexSwitchCheckDefault">Pushing</label>
        <div>
          <small class="form-text text-muted text-nowrap"
            ><small><i class="fas fa-code-branch"></i> to GitHub</small></small
          >
        </div>
      </div>
      <div v-if="remote.isUserRepo" class="form-check form-switch">
        <input
          class="form-check-input"
          type="checkbox"
          id="flexSwitchCheckDefault1"
          :checked="remote.shouldImport"
          @change="confirmToggle('shouldImport', remote.shouldImport, $event)"
        />
        <label class="form-check-label" for="flexSwitchCheckDefault1">Importing</label>
        <div>
          <small class="form-text text-muted text-nowrap"
            ><small><i class="fas fa-file-import"></i> from GitHub</small></small
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
          {{ toggleField === "shouldPush" ? "pushing to " : "importing from " }}
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
  </div>
  <div v-if="showLog" class="mt-3 d-flex">
    <div v-if="remote.lastPushLog" class="card p-2 flex-fill">
      <b><u>Push</u></b>
      <pre class="mb-0" style="white-space: pre-line; text-align: left">
        <small>
          {{ remote.lastPushLog }}
        </small>
      </pre>
    </div>
    <div v-if="remote.lastImportLog" class="card p-2 flex-fill">
      <b><u>Import</u></b>
      <pre class="mb-0" style="white-space: pre-line; text-align: left">
        <small>
          {{ remote.lastImportLog }}
        </small>
      </pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type Modal from "bootstrap/js/dist/modal";
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

const showLog = ref(false);

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
        emit("changed", props.remote);
      },
    }
  );
};
</script>
