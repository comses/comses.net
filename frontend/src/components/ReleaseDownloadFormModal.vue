<template>
  <div>
    <button class="btn btn-primary my-1 w-100" rel="nofollow" @click="modal?.show()">
      <i class="fas fa-download"></i> Download Version {{ versionNumber }}
    </button>
    <BootstrapModal
      id="download-request-modal"
      title="Please complete a brief survey"
      ref="modal"
      centered
    >
      <template #afterTitle>
        <BootstrapTooltip
          class="ps-1"
          title="We use this information to gain a better understanding of our community. If you are signed in, industry and affiliation will be pre-filled from your profile."
        />
      </template>
      <template #body>
        <form @submit="handleSubmit" id="download-request-form">
          <SelectField
            class="mb-3"
            name="industry"
            label="What industry do you work in?"
            :options="industryOptions"
            required
          />
          <ResearchOrgField
            class="mb-3"
            name="affiliation"
            label="What is your institutional affiliation?"
            help=""
            :disabled="isNullAffiliation"
          >
            <template #help>
              <div class="mt-1">
                <input
                  class="form-check-input"
                  type="checkbox"
                  id="check-other-affiliation"
                  @change="setNullAffiliation"
                />
                <label class="form-check-label ms-2" for="check-other-affiliation">
                  <small>Not listed or none</small>
                </label>
              </div>
            </template>
          </ResearchOrgField>
          <SelectField
            name="reason"
            label="What do you plan on using this model for?"
            :options="reasonOptions"
            required
          />
          <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
        </form>
      </template>
      <template #footer>
        <CheckboxField
          v-if="props.userData.authenticated"
          form="download-request-form"
          class="me-auto mb-n1"
          name="saveToProfile"
          label="Remember my answers"
        />
        <button type="button" data-bs-dismiss="modal" class="btn btn-outline-gray">Cancel</button>
        <button type="submit" form="download-request-form" class="btn btn-success">
          <i class="fas fa-download"></i> Download
        </button>
      </template>
    </BootstrapModal>
  </div>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { ref } from "vue";
import { isEmpty } from "lodash-es";
import type Modal from "bootstrap/js/dist/modal";
import type { Organization } from "@/types";
import BootstrapModal from "@/components/BootstrapModal.vue";
import BootstrapTooltip from "@/components/BootstrapTooltip.vue";
import SelectField from "@/components/form/SelectField.vue";
import CheckboxField from "@/components/form/CheckboxField.vue";
import ResearchOrgField from "@/components/form/ResearchOrgField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useForm } from "@/composables/form";
import { useReleaseEditorAPI } from "@/composables/api";

export interface ReleaseDownloadFormProps {
  identifier: string;
  versionNumber: string;
  userData: {
    id: number | null;
    authenticated: boolean;
    industry?: string;
    affiliation?: Organization;
  };
}

const props = defineProps<ReleaseDownloadFormProps>();

const modal = ref<Modal>();

const schema = yup.object().shape({
  industry: yup.string().required(),
  reason: yup.string().required(),
  affiliation: yup
    .object({
      name: yup.string().required(),
      url: yup.string().url().nullable(),
      acronym: yup.string().nullable(),
      rorId: yup.string().nullable(),
    })
    .nullable()
    .default(null),
  saveToProfile: yup.boolean().required().default(false),
});
type ReleaseDownloadFields = yup.InferType<typeof schema>;

const { serverErrors, requestDownload, downloadUrl } = useReleaseEditorAPI();

const { errors, handleSubmit, values } = useForm<ReleaseDownloadFields>({
  schema,
  initialValues: {
    industry: props.userData.industry || "",
    reason: "",
    affiliation: isEmpty(props.userData.affiliation) ? null : props.userData.affiliation,
    saveToProfile: false,
  },
  onSubmit: async () => {
    await requestDownload(props.identifier, props.versionNumber, values, {
      onSuccess: () => {
        modal.value?.hide();
        window.location.href = downloadUrl(props.identifier, props.versionNumber);
      },
    });
  },
});

const industryOptions = [
  { value: "university", label: "College/University" },
  { value: "educator", label: "K-12 Educator" },
  { value: "government", label: "Government" },
  { value: "private", label: "Private" },
  { value: "nonprofit", label: "Non-Profit" },
  { value: "student", label: "Student" },
  { value: "other", label: "Other" },
];

const reasonOptions = [
  { value: "research", label: "Research" },
  { value: "education", label: "Education" },
  { value: "commercial", label: "Commercial" },
  { value: "policy", label: "Policy / Planning" },
  { value: "other", label: "Other" },
];

const isNullAffiliation = ref(false);
function setNullAffiliation() {
  if (isNullAffiliation.value) {
    isNullAffiliation.value = false;
    values.affiliation = null;
  } else {
    isNullAffiliation.value = true;
    values.affiliation = isEmpty(props.userData.affiliation) ? null : props.userData.affiliation;
  }
}
</script>
