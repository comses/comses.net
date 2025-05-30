<template>
  <div>
    <p>
      Detailed metadata helps others discover and reuse your computational models. Please take the
      time to document how to run your computational model, software and data dependencies, accepted
      inputs and expected outputs.
    </p>
    <form @submit="handleSubmit">
      <MarkdownField
        class="mb-3"
        data-cy="release-notes"
        name="releaseNotes"
        label="Release Notes"
        help="Details about this specific release: what's new, improvements to existing features, bug fixes, etc."
        :rows="5"
        required
      />
      <DatepickerField
        class="mb-3"
        data-cy="embargo-end-date"
        name="embargoEndDate"
        label="Embargo End Date"
        help="The date your private release will be automatically made public"
      />
      <SelectField
        class="mb-3"
        data-cy="operating-system"
        name="os"
        label="Operating System"
        help="The operating system(s) this model is compatible with, e.g., Linux, MacOS, Windows"
        :options="osOptions"
        required
      />
      <TaggerField
        class="mb-3"
        data-cy="software-frameworks"
        name="platforms"
        label="Software Framework(s)"
        help=" Modeling software frameworks (e.g., NetLogo, RePast, Mason, CORMAS, Mesa, etc.) used by this model"
        required
      />
      <TaggerField
        class="mb-3"
        data-cy="programming-languages"
        name="programmingLanguages"
        label="Programming Language(s)"
        help=" Programming languages used in this model"
        required
      />
      <TextField
        class="mb-3"
        name="outputDataUrl"
        label="Output Data URL"
        help="A permanent link to the output data generated by this model"
      />
      <MultiSelectField
        class="mb-3"
        data-cy="license"
        name="license"
        label="License"
        track-by="name"
        label-with="name"
        :options="licenseOptions"
        required
      >
        <template #option="{ option }">
          <div class="d-flex align-items-center">
            <a
              v-if="option.url"
              :href="option.url"
              target="_blank"
              rel="noopener noreferrer"
              class="btn btn-sm btn-info"
            >
              View <i class="fas fa-external-link-alt"></i>
            </a>
            <span class="ms-2">{{ option.name }}</span>
          </div>
        </template>
        <template #help>
          <small class="form-text text-muted" aria-describedby="license">
            An open source licence to govern use and redistribution of your computational model. For
            more information and advice about picking an open source license, please check out
            <a target="_blank" href="//choosealicense.com">choosealicense.com</a> or
            <a target="_blank" href="//opensource.org/licenses">opensource.org/licenses</a>.
          </small>
        </template>
      </MultiSelectField>
      <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
      <button
        type="submit"
        class="btn btn-primary mt-3"
        data-cy="save-and-continue"
        :class="{ disabled: isSubmitLoading }"
      >
        <span v-if="isSubmitLoading"><i class="fas fa-spinner fa-spin me-1"></i> Saving... </span>
        <span v-else>Save and Continue</span>
      </button>
    </form>
  </div>
</template>
<script setup lang="ts">
import * as yup from "yup";
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import DatepickerField from "@/components/form/DatepickerField.vue";
import MarkdownField from "@/components/form/MarkdownField.vue";
import TaggerField from "@/components/form/TaggerField.vue";
import TextField from "@/components/form/TextField.vue";
import SelectField from "@/components/form/SelectField.vue";
import MultiSelectField from "@/components/form/MultiSelectField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useForm } from "@/composables/form";
import { useReleaseEditorAPI } from "@/composables/api";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import type { License, CodebaseReleaseMetadata } from "@/types";

const store = useReleaseEditorStore();
const router = useRouter();

const licenseOptions = ref<License[]>([]);
const osOptions = [
  { value: "linux", label: "Unix/Linux" },
  { value: "macos", label: "Mac OS" },
  { value: "windows", label: "Windows" },
  { value: "platform_independent", label: "Operating System Independent" },
  { value: "other", label: "Other" },
];

const schema = yup.object().shape({
  releaseNotes: yup.string().required().label("Release Notes"),
  embargoEndDate: yup.date().nullable().label("Embargo End Date"),
  os: yup.string().required().label("Operating System"),
  platforms: yup
    .array()
    .of(yup.object().shape({ name: yup.string() }))
    .min(1)
    .required()
    .label("Frameworks"),
  programmingLanguages: yup
    .array()
    .of(yup.object().shape({ name: yup.string() }))
    .min(1)
    .required()
    .label("Programming Languages"),
  live: yup.bool(),
  license: yup
    .object()
    .shape({
      name: yup.string().required(),
      url: yup.string().url(),
    })
    .required()
    .label("License"),
  outputDataUrl: yup.string().url().label("Output Data URL"),
});
type ReleaseMetadataFields = yup.InferType<typeof schema>;

const isLoading = ref(true);

const { serverErrors, update, isLoading: isSubmitLoading } = useReleaseEditorAPI();

const { errors, handleSubmit, values, setValues } = useForm<ReleaseMetadataFields>({
  schema,
  initialValues: {},
  showPlaceholder: isLoading,
  onSubmit: async () => {
    await update(store.identifier, store.versionNumber, values);
    if (serverErrors.value.length === 0) {
      store.setMetadata({ ...values } as CodebaseReleaseMetadata);
      router.push({ name: "contributors" });
    }
  },
});

function initializeValuesFromStore() {
  isLoading.value = true;
  setValues({
    ...store.metadata,
  });
  licenseOptions.value = store.release.possibleLicenses;
  isLoading.value = false;
}

onMounted(() => {
  if (store.isInitialized) {
    initializeValuesFromStore();
  }
});

watch(
  () => store.isInitialized,
  () => {
    if (store.isInitialized) {
      initializeValuesFromStore();
    }
  }
);
</script>
