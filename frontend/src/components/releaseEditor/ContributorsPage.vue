<template>
  <div>
    <p>
      Please list the contributors that should be included in a citation for this software release.
      Ordering is important, as is the role of the contributor. You can change ordering by dragging
      contributors in the list.
    </p>
    <p>
      By default, we will always add the submitter (you) as a release contributor. There must be at
      least one contributor for a given release.
    </p>
    <div class="d-flex justify-content-between align-items-end">
      <ContributorAddModal :disabled="reordered" />
      <div v-if="reordered">
        <div class="alert alert-warning px-1 py-0 mb-2">
          <small class="">
            <i class="fas fa-info-circle"></i> Please save your changes once finished re-ordering
          </small>
        </div>
        <div class="d-flex justify-content-end">
          <button
            type="button"
            class="btn btn-sm btn-outline-danger me-2"
            :class="{ disabled: isLoading }"
            @click="revertChanges"
          >
            Revert
          </button>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            :class="{ disabled: isLoading }"
            @click="save()"
          >
            <span v-if="isLoading"> <i class="fas fa-spinner fa-spin"></i> Saving... </span>
            <span v-else><i class="fas fa-save"></i> Save Changes</span>
          </button>
        </div>
      </div>
    </div>
    <Sortable
      :list="releaseContributors"
      :item-key="item => item.contributor.email"
      class="list-group my-3"
      @end="sort"
      tag="ul"
    >
      <template #item="{ element }">
        <li
          :key="element.contributor.id"
          class="list-group-item d-flex justify-content-between"
          style="cursor: move"
        >
          <div class="container">
            <div class="row justify-content-start align-items-center">
              <div class="col-9">
                <div class="d-flex flex-row">
                  <div class="align-self-center pe-3">
                    <i class="fas fa-grip-vertical text-muted"></i>
                  </div>
                  <div class="col">
                    <h5 class="m-0">
                      <a
                        :href="element.profileUrl"
                        target="_blank"
                        data-bs-toggle="tooltip"
                        :title="element.contributor.name + '\'s User Profile'"
                      >
                        <span v-if="element.contributor.user">
                          <i class="fas fa-user fa-xs"></i>
                          {{ element.contributor.name }}
                        </span>
                        <span v-else>
                          {{ element.contributor.name }}
                        </span>
                      </a>
                    </h5>
                    <div>
                      <small class="text-muted"> ({{ roleDisplay(element) }})</small>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-1 d-flex align-items-center">
                <span v-if="element.includeInCitation" class="badge bg-info">citable</span>
              </div>
              <div class="col-2">
                <button
                  type="button"
                  class="btn btn-link btn-sm me-2"
                  :class="{ disabled: reordered }"
                  @click="
                    editCandidate = element;
                    editModal?.show();
                  "
                >
                  <small><i class="fas fa-edit"></i> Edit</small>
                </button>
                <button
                  v-if="releaseContributors.length > 1"
                  type="button"
                  class="btn btn-link text-danger btn-sm"
                  :class="{ disabled: reordered || releaseContributors.length === 1 }"
                  @click="
                    removalCondidate = element;
                    removeConfirmationModal?.show();
                  "
                >
                  <small><i class="fas fa-trash"></i> Remove</small>
                </button>
              </div>
            </div>
          </div>
        </li>
      </template>
    </Sortable>
    <BootstrapModal
      id="remove-confirmation-modal"
      title="Remove Contributor"
      ref="removeConfirmationModal"
      centered
    >
      <template #body>
        <p>Are you sure you want to remove this contributor? This action cannot be undone.</p>
      </template>
      <template #footer>
        <button
          type="button"
          class="btn btn-outline-gray"
          :class="{ disabled: isLoading }"
          data-bs-dismiss="modal"
        >
          Cancel
        </button>
        <button
          type="button"
          class="btn btn-danger"
          :class="{ disabled: isLoading }"
          @click="removeContributor"
        >
          <span v-if="isLoading"> <i class="fas fa-spinner fa-spin me-1"></i> Removing... </span>
          <span v-else> Remove </span>
        </button>
      </template>
    </BootstrapModal>
    <BootstrapModal
      id="edit-contributor-modal"
      title="Edit Contributor"
      ref="editModal"
      size="lg"
      centered
    >
      <template #content>
        <ContributorEditForm
          id="edit-contributor-form"
          :show-custom-input="true"
          :contributor="editCandidate"
          @success="() => editModal?.hide()"
        />
      </template>
    </BootstrapModal>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, watchEffect } from "vue";
import { Sortable } from "sortablejs-vue3";
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ContributorAddModal from "@/components/releaseEditor/ContributorAddModal.vue";
import ContributorEditForm from "@/components/releaseEditor/ContributorEditForm.vue";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import type { ReleaseContributor } from "@/types";
import type { SortableEvent } from "sortablejs";
import { useReleaseEditorAPI } from "@/composables/api";

const store = useReleaseEditorStore();

const removeConfirmationModal = ref<Modal>();
const editModal = ref<Modal>();

const roleLookup = {
  author: "Author",
  publisher: "Publisher",
  resourceProvider: "Resource Provider",
  maintainer: "Maintainer",
  pointOfContact: "Point of Contact",
  editor: "Editor",
  contributor: "Contributor",
  collaborator: "Collaborator",
  funder: "Funder",
  copyrightHolder: "Copyright Holder",
};

const releaseContributors = ref<ReleaseContributor[]>([]);
const removalCondidate = ref<ReleaseContributor>();
const editCandidate = ref<ReleaseContributor>();
const reordered = ref(false);
const isLoading = ref(false);

const { serverErrors, updateContributors } = useReleaseEditorAPI();

function revertChanges() {
  initializeFromStore();
  reordered.value = false;
}

async function save(onSuccess?: () => void) {
  isLoading.value = true;
  await updateContributors(store.identifier, store.versionNumber, releaseContributors.value);
  if (serverErrors.value.length === 0) {
    await store.fetchCodebaseRelease(store.identifier, store.versionNumber);
    reordered.value = false;
    if (onSuccess) onSuccess();
  }
  isLoading.value = false;
}

async function removeContributor() {
  if (!removalCondidate.value) return;
  const index = removalCondidate.value.index;
  if (index === undefined) return;
  releaseContributors.value.splice(index, 1);
  await save(() => {
    removeConfirmationModal.value?.hide();
  });
}

function sort(event: SortableEvent) {
  const { newIndex, oldIndex } = event;
  if (newIndex !== undefined && oldIndex !== undefined && newIndex !== oldIndex) {
    reordered.value = true;
    const item = releaseContributors.value.splice(oldIndex, 1)[0];
    releaseContributors.value.splice(newIndex, 0, item);
    // sync the index property used to track order with the array ordering
    releaseContributors.value.forEach((contributor, index) => {
      contributor.index = index;
    });
  }
}

function roleDisplay(contributor: ReleaseContributor) {
  return contributor.roles
    ?.map((role: string) => roleLookup[role as keyof typeof roleLookup])
    .join(", ");
}

function initializeFromStore() {
  releaseContributors.value = JSON.parse(JSON.stringify(store.releaseContributors));
}

onMounted(() => {
  if (store.isInitialized) {
    initializeFromStore();
  }
});

watchEffect(() => {
  if (store.isInitialized) {
    initializeFromStore();
  }
});
</script>
