<template>
  <div class="modal-body">
    <form @submit="handleSubmit" :id="id">
      <span v-if="showCustomInput">
        <SelectField
          class="mb-3"
          name="type"
          label="Contributor Type"
          :options="typeOptions"
          required
        />
        <div class="card mb-3">
          <div v-if="isPerson" class="card-header">
            <UserSearch
              label="Search for an Existing User"
              placeholder="Skip entering contributor details by searching for users already in our system"
              :search-fn="search"
              :errors="profileErrors"
              @select="populateFromUser($event)"
              show-avatar
              show-email
              show-affiliation
            />
          </div>
          <div class="card-body">
            <TextField
              v-if="!isPerson"
              class="mb-3"
              name="givenName"
              label="Organization Name"
              required
            />
            <div v-else class="row">
              <div class="col-4 pe-0">
                <TextField class="mb-3" name="givenName" label="First Name" required />
              </div>
              <div class="col-3 pe-0">
                <TextField class="mb-3" name="middleName" label="Middle Name" />
              </div>
              <div class="col-5">
                <TextField class="mb-3" name="familyName" label="Last Name" required />
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
      <CheckboxField name="includeInCitation" label="Include in Citation?" />
      <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
    </form>
  </div>
  <div class="modal-footer border-0">
    <button
      type="button"
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
    contributor?: ReleaseContributor;
    onSuccess?: () => void;
  }>(),
  {
    showCustomInput: false,
  }
);

const emit = defineEmits(["success"]);

const { serverErrors: profileErrors, search } = useProfileAPI();

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
  roles: [],
  includeInCitation: true,
};

const { errors, handleSubmit, values, setValues } = useForm<ContributorFields>({
  schema,
  initialValues,
  onSubmit: async () => {
    if (!hasName.value) return;

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
    if (serverErrors.value.length === 0) {
      isLoading.value = true;
      await store.fetchCodebaseRelease(store.identifier, store.versionNumber);
      isLoading.value = false;
      setValues(initialValues);
      emit("success");
    }
  },
});

const isLoading = ref(false);
const isPerson = computed(() => values.type === "person");

const hasName = computed(() => values.user || values.givenName);

function populateFromReleaseContributor(contributor: ReleaseContributor) {
  setValues({
    user: contributor.contributor.user || null,
    email: contributor.contributor.email,
    givenName: contributor.contributor.givenName,
    familyName: contributor.contributor.familyName,
    middleName: contributor.contributor.middleName,
    affiliations: contributor.contributor.affiliations,
    type: contributor.contributor.type,
    roles: contributor.roles,
    includeInCitation: contributor.includeInCitation,
  });
}

function populateFromContributor(contributor: Contributor | null) {
  setValues({
    ...values,
    ...contributor,
  });
}

function resetContributor() {
  setValues(initialValues);
}

function populateFromUser(user: any) {
  setValues({
    ...values,
    user,
    givenName: user.givenName,
    familyName: user.familyName,
    email: user.email,
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
