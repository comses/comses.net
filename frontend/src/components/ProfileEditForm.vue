<template>
  <form @submit="handleSubmit">
    <div class="row">
      <div class="mb-3 col-3">
        <h3>Profile image</h3>
        <label style="cursor: pointer; margin-top: -20px" for="profileUpload" class="form-label">
          <img
            class="mt-3 d-block rounded img-fluid img-thumbnail"
            alt="Profile Image"
            v-if="values.avatar"
            :src="values.avatar"
          />
          <img
            class="mt-3 d-block rounded img-fluid img-thumbnail"
            alt="Click to edit"
            data-src="holder.js/150x150?text=Click to edit"
            v-else
          />
        </label>
        <input
          id="profileUpload"
          type="file"
          accept=".gif,.jpg,.jpeg,.png"
          class="d-none form-control-file"
          @change="uploadImage"
        />
      </div>

      <div class="mb-3 col-9">
        <h3>Social Authentication and Membership</h3>
        <ul class="list-group">
          <li class="list-group-item">
            <span v-if="values.githubUrl">
              <a :href="values.githubUrl"
                ><i class="text-gray fab fa-github"></i> {{ values.githubUrl }}</a
              >
              <a :href="connectionsUrl" title="Manage connected GitHub account">
                <i class="float-end fas fa-edit"></i>
              </a>
            </span>
            <span v-else>
              <a :href="connectionsUrl">
                <i class="text-gray fab fa-github"></i> Connect your GitHub account
              </a>
            </span>
          </li>
          <li class="list-group-item">
            <span v-if="values.orcidUrl">
              <a :href="values.orcidUrl"
                ><i class="text-gray fab fa-orcid"></i> {{ values.orcidUrl }}</a
              >
              <a :href="connectionsUrl" title="Manage connected ORCID account">
                <i class="float-end fas fa-edit"></i>
              </a>
            </span>
            <span v-else>
              <a :href="connectionsUrl">
                <i class="text-gray fab fa-orcid"></i> Connect your ORCID account
              </a>
            </span>
          </li>
          <li class="list-group-item">
            <CheckboxField
              :required="false"
              name="fullMember"
              :errorMsgs="errors.fullMember"
              label="Full Member"
            >
              <template #help>
                <div class="form-text text-muted">
                  By checking this box, I agree to the
                  <a href="#" data-bs-toggle="modal" data-bs-target="#membership-modal">
                    rights and responsibilities
                  </a>
                  of CoMSES Net Full Membership.
                </div>
              </template>
            </CheckboxField>
          </li>
          <li class="list-group-item">
            <p>Peer Reviewer Profile</p>
            <ProfileEditReviewer
              :reviewer="reviewer"
              :memberProfile="data"
              @update="r => (reviewer = r)"
            />
          </li>
        </ul>
      </div>
    </div>

    <div class="row">
      <div class="col-6">
        <TextField class="mb-3" data-cy="first-name" name="givenName" label="First Name" required />
      </div>
      <div class="col-6">
        <TextField class="mb-3" data-cy="last-name" name="familyName" label="Last Name" required />
      </div>
    </div>
    <TextField
      class="mb-3"
      name="email"
      label="Email"
      help="Email changes require reverification of your new email address by acknowledging a confirmation email"
      required
    />
    <MarkdownField
      class="mb-3"
      name="bio"
      label="Bio"
      help="A brief description of your research career"
      :rows="5"
    />
    <MarkdownField
      class="mb-3"
      name="researchInterests"
      label="Research Interests"
      help="A brief description of your research interests"
      :rows="5"
    />
    <TextField
      class="mb-3"
      name="personalUrl"
      label="Personal URL"
      help="A link to your personal website"
    />
    <TextField
      class="mb-3"
      name="professionalUrl"
      label="Professional URL"
      help="A link to your institutional or professional profile page"
    />
    <SelectField
      class="mb-3"
      name="industry"
      label="Industry"
      help="Your primary field of work"
      :options="industryOptions"
    />
    <ResearchOrgListField
      class="mb-3"
      name="affiliations"
      label="Affiliations"
      help="A list of organizations that you are affiliated with"
    />
    <TextListField
      class="mb-3"
      name="degrees"
      label="Degrees"
      help="A list of degrees earned and their associated institutions: e.g., Ph.D., Environmental Social Science, Arizona State University"
    />
    <TaggerField class="mb-3" name="tags" label="Keywords" type="Profile" />
    <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
    <button type="submit" data-cy="submit" class="btn btn-primary mb-3" :disabled="isLoading">
      Save
    </button>
  </form>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { ref, onBeforeUnmount, onMounted } from "vue";
import CheckboxField from "@/components/form/CheckboxField.vue";
import TextField from "@/components/form/TextField.vue";
import TextListField from "@/components/form/TextListField.vue";
import SelectField from "@/components/form/SelectField.vue";
import MarkdownField from "@/components/form/MarkdownField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import ResearchOrgListField from "@/components/form/ResearchOrgListField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import ProfileEditReviewer from "@/components/ProfileEditReviewer.vue";
import { useForm } from "@/composables/form";
import { useProfileAPI, useReviewEditorAPI } from "@/composables/api";
import type { Reviewer } from "@/types";

const props = defineProps<{
  userId: number;
  connectionsUrl: string;
}>();

const reviewer = ref<Reviewer | null>();

const schema = yup.object().shape({
  avatar: yup.string().nullable(),
  givenName: yup.string().required().label("First name"),
  familyName: yup.string().required().label("Last name"),
  email: yup.string().email().required().label("Email"),
  researchInterests: yup.string().label("Research interests"),
  orcidUrl: yup.string().url().nullable(),
  githubUrl: yup.string().url().nullable(),
  personalUrl: yup.string().url().label("Personal URL"),
  professionalUrl: yup.string().url().label("Professional URL"),
  industry: yup.string().nullable().label("Industry"),
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
    .nullable()
    .label("Affiliations"),
  bio: yup.string().label("Bio"),
  degrees: yup.array().of(yup.string().required()).label("Degrees"),
  tags: yup
    .array()
    .of(yup.object().shape({ name: yup.string().required() }))
    .label("Tags"),
  fullMember: yup.boolean().required().label("Full Member"),
  peerReviewerId: yup.number().nullable(),
});
type ProfileEditFields = yup.InferType<typeof schema>;

const industryOptions = [
  { value: "university", label: "College/University" },
  { value: "educator", label: "K-12 Educator" },
  { value: "government", label: "Government" },
  { value: "private", label: "Private" },
  { value: "nonprofit", label: "Non-Profit" },
  { value: "student", label: "Student" },
  { value: "other", label: "Other" },
];

const { data, serverErrors, retrieve, update, isLoading, detailUrl, uploadProfilePicture } =
  useProfileAPI();
const { retrieveReviewer } = useReviewEditorAPI();

const {
  errors,
  handleSubmit,
  values,
  setValues,
  addUnsavedAlertListener,
  removeUnsavedAlertListener,
} = useForm<ProfileEditFields>({
  schema,
  initialValues: {
    tags: [],
  },
  showPlaceholder: isLoading,
  onSubmit: async () => {
    await update(props.userId, values, {
      onSuccess: () => {
        window.location.href = detailUrl(props.userId);
      },
    });
  },
});

onMounted(async () => {
  await retrieve(props.userId);
  setValues(data.value);
  if (values.peerReviewerId) {
    const response = await retrieveReviewer(values.peerReviewerId);
    reviewer.value = response.data;
  } else {
    reviewer.value = null;
  }
  addUnsavedAlertListener();
});

onBeforeUnmount(() => {
  removeUnsavedAlertListener();
});

async function uploadImage(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = (target.files as FileList)?.[0];
  const response = await uploadProfilePicture(props.userId, file);
  values.avatar = response.data;
}
</script>
