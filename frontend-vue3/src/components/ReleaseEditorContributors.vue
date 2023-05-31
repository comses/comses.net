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
      <ReleaseEditorContributorAddModal :disabled="reordered" />
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
      :item-key="item => item"
      class="list-group my-3"
      @end="sort"
      tag="ul"
    >
      <template #item="{ element }">
        <li
          :key="element"
          class="list-group-item d-flex justify-content-between"
          style="cursor: move"
        >
          <div class="d-flex">
            <div class="align-self-center pe-3">
              <i class="fas fa-grip-vertical text-muted"></i>
            </div>
            <div>
              <div class="d-flex align-items-end">
                <h5 class="m-0">{{ displayName(element.contributor) }}</h5>
                <small class="text-muted ms-2">({{ roleDisplay(element) }})</small>
                <span v-if="element.include_in_citation" class="badge bg-info ms-2">citable</span>
              </div>
              <small>
                <a :href="element.profile_url" target="_blank">
                  <span v-if="element.contributor.user">
                    <i class="fas fa-user"></i>
                    {{ element.contributor.user.username }}
                  </span>
                  <span v-else>
                    {{ displayName(element.contributor) }}
                  </span>
                </a>
              </small>
            </div>
          </div>
          <div class="d-flex align-items-center">
            <button
              type="button"
              class="btn btn-link btn-sm me-2"
              :class="{ disabled: reordered }"
              @click="
                editCandidate = element;
                editModal.show();
              "
            >
              <small><i class="fas fa-edit"></i> Edit</small>
            </button>
            <button
              type="button"
              class="btn btn-link text-danger btn-sm"
              :class="{ disabled: reordered }"
              @click="
                removalCondidate = element;
                removeConfirmationModal.show();
              "
            >
              <small>Remove</small>
            </button>
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
        <ReleaseEditorContributorEditForm
          id="edit-contributor-form"
          :show-custom-input="true"
          :contributor="editCandidate"
          @success="() => editModal.hide()"
        />
      </template>
    </BootstrapModal>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, watchEffect } from "vue";
import { Sortable } from "sortablejs-vue3";
import type { Modal } from "bootstrap";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReleaseEditorContributorAddModal from "@/components/ReleaseEditorContributorAddModal.vue";
import ReleaseEditorContributorEditForm from "@/components/ReleaseEditorContributorEditForm.vue";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import type { Contributor, ReleaseContributor } from "@/types";
import type { SortableEvent } from "sortablejs";
import { useReleaseEditorAPI } from "@/composables/api";

const store = useReleaseEditorStore();

const removeConfirmationModal = ref<typeof Modal>();
const editModal = ref<typeof Modal>();

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
    removeConfirmationModal.value.hide();
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

function displayName(contributor: Contributor) {
  const { given_name, family_name, user } = contributor;
  let name = [given_name, family_name].filter(Boolean).join(" ");
  if (!name && user && user.name) {
    name = user.name;
  }
  return name;
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
