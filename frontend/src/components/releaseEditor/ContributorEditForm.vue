<template>
  <div class="modal-body">
    <form @submit="handleSubmit" @reset="handleReset" :id="id">
      <span v-if="showCustomInput">
        <SelectField
          class="mb-3"
          name="type"
          label="Contributor Type"
          @change="changeContributorType"
          :options="typeOptions"
          :disabled="disableEditForm"
          required
        />
        <div class="card mb-3">
          <div v-if="isPerson" class="card-header">
            <UserSearch
              label="Search for an existing User"
              placeholder="Skip entering contributor details by searching for users already in our system"
              :search-fn="search"
              :errors="profileErrors"
              @select="populateFromUser($event)"
              show-avatar
              show-email
              show-affiliation
            />
          </div>
          <div style="position: relative">
            <!-- Container element with relative positioning -->
            <div
              v-if="disableEditForm"
              class="position-absolute top-0 start-0 w-100 h-100 bg-light opacity-50"
              style="z-index: 3"
            ></div>
            <div class="card-body">
              <div v-if="!isPerson">
                <ResearchOrgListField
                  name="jsonAffiliations"
                  placeholder="Type to find organizations"
                  @change="setOrganizationGivenName"
                  :is-contributor-organization="!isPerson"
                  label="Research Organization Registry Lookup"
                />
                <TextField
                  class="mb-3"
                  name="givenName"
                  label="Organization Name"
                  disabled
                  required
                />
              </div>
              <div v-else class="row">
                <div class="col-4 pe-0">
                  <TextField
                    class="mb-3"
                    name="givenName"
                    label="First Name"
                    required
                    :disabled="disableEditForm"
                  />
                </div>
                <div class="col-3 pe-0">
                  <TextField
                    class="mb-3"
                    name="middleName"
                    label="Middle Name"
                    :disabled="disableEditForm"
                  />
                </div>
                <div class="col-5">
                  <TextField
                    class="mb-3"
                    name="familyName"
                    label="Last Name"
                    required
                    :disabled="disableEditForm"
                  />
                </div>
              </div>
              <div v-if="isPerson">
                <TextField
                  class="mb-3"
                  name="email"
                  label="Email"
                  required
                  :disabled="disableEditForm"
                />
                <ResearchOrgListField
                  name="jsonAffiliations"
                  placeholder="Type to find organizations"
                  label="Affiliations"
                  :disabled="disableEditForm"
                />
              </div>
            </div>
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
        :disabled="disableEditForm"
      />
      <CheckboxField name="includeInCitation" label="Include in citation?" />
      <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
    </form>
  </div>
  <div class="modal-footer border-0">
    <button v-if="!isEdit" type="button" class="btn btn-outline-gray" @click="emit('reset')">
      Reset
    </button>
    <button
      type="reset"
      class="btn btn-outline-gray"
      :class="{ disabled: isLoading }"
      data-bs-dismiss="modal"
    >
      Cancel
    </button>
    <button
      type="submit"
      class="btn btn-primary"
      :class="{ disabled: isLoading || !hasName }"
      :form="id"
    >
      <span v-if="isLoading"> <i class="fas fa-spinner fa-spin me-1"></i> Saving... </span>
      <span v-else> <i class="fas fa-user-plus me-1"></i> Save </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { computed, ref, watch } from "vue";
import ResearchOrgListField from "@/components/form/ResearchOrgListField.vue";
import TextField from "@/components/form/TextField.vue";
import CheckboxField from "@/components/form/CheckboxField.vue";
import SelectField from "@/components/form/SelectField.vue";
import MultiSelectField from "@/components/form/MultiSelectField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import UserSearch from "@/components/UserSearch.vue";
import { useForm } from "@/composables/form";
import { useReleaseEditorAPI, useProfileAPI } from "@/composables/api";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import type { Contributor, ReleaseContributor } from "@/types";

const props = withDefaults(
  defineProps<{
    id: string;
    showCustomInput?: boolean;
    disableEditForm?: boolean;
    contributor?: ReleaseContributor;
    onSuccess?: () => void;
    isEdit?: boolean;
  }>(),
  {
    showCustomInput: false,
    disableEditForm: true,
    isEdit: true,
  }
);

const emit = defineEmits(["success", "reset"]);

const { serverErrors: profileErrors, search } = useProfileAPI();

const store = useReleaseEditorStore();
const disableEditForm = computed(() => !!values.user || props.disableEditForm);
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
const roleOptions = Object.keys(roleLookup);

const typeOptions = [
  { value: "person", label: "Person" },
  { value: "organization", label: "Organization" },
];

const schema = yup.object().shape({
  user: yup.mixed().nullable().label("User"),
  email: yup.string().email().nullable().label("Email"),
  givenName: yup.string().nullable().label("First name/Organization name"),
  familyName: yup.string().nullable().label("Last name"),
  middleName: yup.string().nullable().label("Middle name"),
  affiliations: yup
    .array()
    .of(
      yup.object({
        name: yup.string().required(),
        url: yup.string().url().nullable(),
        acronym: yup.string().nullable(),
        rorId: yup.string().nullable(),
      })
    )
    .label("Affiliations"),
  jsonAffiliations: yup
    .array()
    .of(
      yup.object({
        name: yup.string().required(),
        url: yup.string().url().nullable(),
        acronym: yup.string().nullable(),
        rorId: yup.string().nullable(), // assuming "rorId" is the correct key, not "ror_id"
      })
    )
    .label("JSON Affiliations"),
  type: yup.string().oneOf(["person", "organization"]).default("person"),
  roles: yup.array().of(yup.string()).min(1).label("Roles"),
  includeInCitation: yup.bool().required().label("Include in citation"),
});

type ContributorFields = yup.InferType<typeof schema>;

const { serverErrors, updateContributors } = useReleaseEditorAPI();

const initialValues: ContributorFields = {
  type: "person",
  user: null,
  affiliations: [],
  jsonAffiliations: [],
  roles: [],
  includeInCitation: true,
};

const { errors, handleSubmit, handleReset, values, setValues } = useForm<ContributorFields>({
  schema,
  initialValues,
  onSubmit: async () => {
    if (!hasName.value) return;
    isLoading.value = true;
    let contributors = JSON.parse(JSON.stringify(store.releaseContributors));
    const newContributor = {
      contributor: {
        user: values.user,
        type: values.type,
        email: values.email,
        givenName: values.givenName,
        familyName: values.familyName,
        middleName: values.middleName,
        affiliations: values.affiliations,
        jsonAffiliations: values.jsonAffiliations,
      },
      roles: values.roles,
      includeInCitation: values.includeInCitation,
    };
    if (props.contributor) {
      const index = contributors.findIndex(
        (c: ReleaseContributor) => c.index === props.contributor?.index
      );
      contributors[index] = {
        ...contributors[index],
        ...newContributor,
      };
    } else {
      contributors.push(newContributor);
    }

    await updateContributors(store.identifier, store.versionNumber, contributors);
    isLoading.value = false;
    if (serverErrors.value.length === 0) {
      await store.fetchCodebaseRelease(store.identifier, store.versionNumber);
      setValues(initialValues);
      emit("success");
    }
  },
});

const isLoading = ref(false);
const isPerson = computed(() => values.type === "person");
const hasName = computed(() => values.user || values.givenName);

function populateFromReleaseContributor(releaseContributor: ReleaseContributor) {
  const user = releaseContributor.contributor.user;

  // releaseContributor has an associated user! Take values from the user.
  const givenName = user ? user.memberProfile.givenName : releaseContributor.contributor.givenName;
  const familyName = user
    ? user.memberProfile.familyName
    : releaseContributor.contributor.familyName;

  setValues({
    // set this to get the id from autocomplete contributor
    // id: releaseContributor.contributor.id,
    user: releaseContributor.contributor.user || null,
    email: releaseContributor.contributor.email,
    givenName: givenName,
    familyName: familyName,
    middleName: releaseContributor.contributor.middleName,
    // affiliations: releaseContributor.contributor.affiliations,
    jsonAffiliations: releaseContributor.contributor.jsonAffiliations,
    type: releaseContributor.contributor.type,
    roles: releaseContributor.roles,
    includeInCitation: releaseContributor.includeInCitation,
  });
}

function populateFromContributor(contributor: Contributor | null) {
  setValues({
    ...values,
    ...contributor,
  });
}

function hasPersonData() {
  return values.user || values.givenName || values.familyName || values.email;
}

function changeContributorType() {
  // reset contributors if we switch to an organization and there was a previous user set
  if (values.type === "organization" && hasPersonData()) {
    resetContributor();
  }
}

function resetContributor() {
  setValues(initialValues);
  serverErrors.value = [];
  handleReset();
}

function setOrganizationGivenName() {
  const firstOrganization = (values as any).jsonAffiliations[0];
  values.givenName = firstOrganization ? firstOrganization.name : "";
}

function populateFromUser(user: any) {
  setValues({
    ...values,
    user,
    givenName: user.givenName,
    familyName: user.familyName,
    middleName: "",
    email: user.email,
    jsonAffiliations: user.affiliations,
  });
}

watch(
  () => props.contributor,
  () => {
    if (props.contributor) {
      populateFromReleaseContributor(props.contributor);
    }
  }
);

defineExpose({
  populateFromContributor,
  resetContributor,
});
</script>
