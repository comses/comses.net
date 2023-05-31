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
    <ReleaseEditorContributorEditModal />
    <Sortable :list="store.releaseContributors" :item-key="item => item.id" class="list-group my-3">
      <template #item="{ element, index }">
        <li class="list-group-item d-flex justify-content-between">
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
            <button type="button" class="btn btn-link btn-sm me-2" @click="editContributor(index)">
              <small><i class="fas fa-edit"></i> Edit</small>
            </button>
            <button
              type="button"
              class="btn btn-link text-danger btn-sm"
              @click="removeContributor(index)"
            >
              <small>Remove</small>
            </button>
          </div>
        </li>
      </template>
    </Sortable>
  </div>
</template>
<script setup lang="ts">
import { Sortable } from "sortablejs-vue3";
// import type { SortableEvent } from "sortablejs";
import ReleaseEditorContributorEditModal from "@/components/ReleaseEditorContributorEditModal.vue";
// import { useReleaseEditorAPI } from "@/composables/api";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import type { Contributor, ReleaseContributor } from "@/types";

const store = useReleaseEditorStore();

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
  copyrightholder: "Copyright Holder",
};

// TODO: show edit modal (in a minified state?) then save as normal
function editContributor(index: number) {
  console.log("EDIT", index);
}

// TODO: handle dragging, and consider using a save button for this instead of spamming requests on each drag action

// TODO: show confirmation modal then save after removing contributor
function removeContributor(index: number) {
  console.log("REMOVE", index);
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
</script>
