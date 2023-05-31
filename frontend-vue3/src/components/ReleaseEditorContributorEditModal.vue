<template>
  <button type="button" class="btn btn-primary" rel="nofollow" @click="editContributorModal.show()">
    <i class="fas fa-plus-square me-1"></i> Add a Contributor
  </button>
  <BootstrapModal
    id="edit-contributor-modal"
    title="Add/Edit Contributor"
    ref="editContributorModal"
    size="lg"
    centered
  >
    <template #body>
      <div>
        <form @submit="handleSubmit" id="edit-contributor-form">
          <div v-if="!showCustomInput" class="d-flex align-items-end justify-content-between mb-3">
            <div class="flex-grow-1">
              <ReleaseEditorContributorSearch @select="populateFromContributor($event)" />
            </div>
            <div class="text-center mb-2 mx-3">
              <small class="text-muted">OR</small>
            </div>
            <div>
              <div class="text-center">
                <button
                  type="button"
                  class="btn btn-outline-secondary w-100"
                  @click="showCustomInput = true"
                >
                  <i class="fas fa-plus"></i> Create a New Contributor
                </button>
              </div>
            </div>
          </div>
          <span v-else>
            <button
              type="button"
              class="btn btn-outline-secondary mb-3"
              @click="showCustomInput = false"
            >
              <i class="fas fa-angle-left me-1"></i> Search for Existing Contributors
            </button>
            <SelectField
              class="mb-3"
              name="type"
              label="Contributor Type"
              :options="typeOptions"
              required
            />
            <div class="card mb-3">
              <div v-if="isPerson" class="card-header">
                <ReleaseEditorUserSearch @select="populateFromUser($event)" />
              </div>
              <div class="card-body">
                <TextField
                  v-if="!isPerson"
                  class="mb-3"
                  name="given_name"
                  label="Organization Name"
                  required
                />
                <div v-else class="row">
                  <div class="col-4 pe-0">
                    <TextField class="mb-3" name="given_name" label="First Name" required />
                  </div>
                  <div class="col-3 pe-0">
                    <TextField class="mb-3" name="middle_name" label="Middle Name" />
                  </div>
                  <div class="col-5">
                    <TextField class="mb-3" name="family_name" label="Last Name" required />
                  </div>
                </div>
                <TextField v-if="isPerson" class="mb-3" name="email" label="Email" required />
                <ResearchOrgListField
                  name="affiliations"
                  placeholder="Type to find organizations"
                  label="Affiliations"
                />
              </div>
            </div>
          </span>

          <MultiSelectField
            class="mb-3"
            name="roles"
            :options="roleOptions"
            :custom-label="(option: string) => roleLookup[option as keyof typeof roleLookup]"
            label="Roles"
            placeholder="Add contributor's role(s)"
            multiple
            required
          />
          <CheckboxField name="include_in_citation" label="Include in Citation?" />
          <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
        </form>
      </div>
    </template>
    <template #footer>
      <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
      <button type="submit" class="btn btn-primary" form="edit-contributor-form">
        <span v-if="isLoading"> <i class="fas fa-spinner fa-spin me-1"></i> Saving... </span>
        <span v-else> <i class="fas fa-user-plus me-1"></i> Save </span>
      </button>
    </template>
  </BootstrapModal>
</template>
<script setup lang="ts">
import * as yup from "yup";
import { computed, ref } from "vue";
import type { Modal } from "bootstrap";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ResearchOrgListField from "@/components/form/ResearchOrgListField.vue";
import TextField from "@/components/form/TextField.vue";
import CheckboxField from "@/components/form/CheckboxField.vue";
import SelectField from "@/components/form/SelectField.vue";
import MultiSelectField from "@/components/form/MultiSelectField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import ReleaseEditorUserSearch from "@/components/ReleaseEditorUserSearch.vue";
import ReleaseEditorContributorSearch from "@/components/ReleaseEditorContributorSearch.vue";
import { useForm } from "@/composables/form";
import { useReleaseEditorAPI } from "@/composables/api";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import type { Contributor } from "@/types";

const store = useReleaseEditorStore();

const editContributorModal = ref<typeof Modal>();

const showCustomInput = ref(false);

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
const roleOptions = Object.keys(roleLookup);

const typeOptions = [
  { value: "person", label: "Person" },
  { value: "organization", label: "Organization" },
];

const schema = yup.object().shape({
  user: yup.mixed().nullable().label("User"),
  email: yup.string().email().nullable().label("Email"),
  given_name: yup.string().nullable().label("First name/Organization name"),
  family_name: yup.string().nullable().label("Last name"),
  middle_name: yup.string().nullable().label("Middle name"),
  affiliations: yup
    .array()
    .of(
      yup.object({
        name: yup.string().required(),
        url: yup.string().url().nullable(),
        acronym: yup.string().nullable(),
        ror_id: yup.string().nullable(),
      })
    )
    .label("Affiliations"),
  type: yup.string().oneOf(["person", "organization"]).default("person"),
  roles: yup.array().of(yup.string()).min(1).label("Roles"),
  include_in_citation: yup.bool().required().label("Include in citation"),
});

type ContributorFields = yup.InferType<typeof schema>;

const { serverErrors, updateContributors } = useReleaseEditorAPI();

const { errors, handleSubmit, values, setValues } = useForm<ContributorFields>({
  schema,
  initialValues: {
    type: "person",
    affiliations: [],
    roles: [],
    include_in_citation: true,
  },
  onSubmit: async () => {
    const newContributor = {
      contributor: {
        user: values.user,
        type: values.type,
        email: values.email,
        given_name: values.given_name,
        family_name: values.family_name,
        middle_name: values.middle_name,
        affiliations: values.affiliations,
      },
      roles: values.roles,
      include_in_citation: values.include_in_citation,
    };
    const contributors = [...store.releaseContributors, newContributor];
    await updateContributors(store.identifier, store.versionNumber, contributors);
    if (serverErrors.value.length === 0) {
      isLoading.value = true;
      await store.fetchCodebaseRelease(store.identifier, store.versionNumber);
      isLoading.value = false;
      editContributorModal.value.hide();
    }
    console.log(values);
  },
});

const isLoading = ref(false);
const isPerson = computed(() => values.type === "person");

function populateFromContributor(contributor: Contributor) {
  setValues({
    include_in_citation: true,
    ...contributor,
  });
}

function populateFromUser(user: any) {
  setValues({
    ...values,
    user,
    given_name: user.given_name,
    family_name: user.family_name,
    email: user.email,
  });
}
</script>
