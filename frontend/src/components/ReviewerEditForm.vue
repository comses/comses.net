<template>
  <div class="modal-body">
    <form @submit="handleSubmit" @reset="handleReset">
      <!-- FIXME: hide this and show profile after setting -->
      <div v-if="!props.memberProfileId">
        <UserSearch
          v-if="!values.memberProfile"
          class="mb-3"
          label="Search for an existing User"
          placeholder="Skip entering contributor details by searching for users already in our system"
          :search-fn="search"
          :errors="profileErrors"
          @select="setMemberProfile($event)"
          show-avatar
          show-email
          show-affiliation
        />
        <div class="container" v-else>
          <div class="row py-2">
            <div class="col-2 ps-0">
              <img
                v-if="values.memberProfile.avatarUrl"
                class="d-block img-thumbnail"
                :src="values.memberProfile.avatarUrl"
                alt="Profile Image"
              />
              <img
                v-else
                class="d-block img-thumbnail"
                data-src="holder.js/100x100?text=No Picture Available"
                alt="No Picture Available"
              />
            </div>
            <div class="col-10 pe-0">
              <h2>
                {{ values.memberProfile.name }}
                <button
                  v-if="!props.memberProfileId && !isEdit"
                  class="btn btn-danger float-end"
                  @click="values.memberProfile = null"
                  type="button"
                >
                  Remove
                </button>
              </h2>
              <div class="tag-list">
                <div class="tag mx-1" v-for="tag in values.memberProfile.tags" :key="tag.name">
                  {{ tag.name }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <TextListField
        class="mb-3"
        name="programmingLanguages"
        label="Programming Languages"
        help="A list of programming languages the reviewer is familiar with."
        required
      />
      <TextListField
        class="mb-3"
        name="subjectAreas"
        label="Subject Areas"
        help="Areas of extertise for this reviewer."
        required
      />
      <TextareaField
        class="mb-3"
        name="notes"
        label="Notes"
        help="Any additional notes about this reviewer."
      />
      <FormAlert :validation-errors="Object.values(errors)" :server-errors="serverErrors" />
      <div class="modal-footer border-0">
        <button type="button" class="btn btn-outline-gray" @click="resetForm">Reset</button>
        <button type="submit" class="btn btn-primary" :disabled="isLoading">
          {{ props.isEdit ? "Update" : "Create" }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import * as yup from "yup";
import { onBeforeUnmount, onMounted, watch } from "vue";
import UserSearch from "@/components/UserSearch.vue";
import TextareaField from "@/components/form/TextareaField.vue";
import TextListField from "@/components/form/TextListField.vue";
import FormAlert from "@/components/form/FormAlert.vue";
import { useForm } from "@/composables/form";
import { useProfileAPI, useReviewEditorAPI } from "@/composables/api";
import type { RelatedMemberProfile, Reviewer } from "@/types";

export interface ReviewerEditFormProps {
  reviewer?: Reviewer;
  memberProfileId?: number;
  isEdit?: boolean;
}

const props = withDefaults(defineProps<ReviewerEditFormProps>(), {
  isEdit: false,
});

const schema = yup.object().shape({
  memberProfileId: yup.number().required(),
  memberProfile: yup.mixed<RelatedMemberProfile>().nullable().label("Member profile"),
  programmingLanguages: yup.array().of(yup.string().required()).label("Programming Languages"),
  subjectAreas: yup.array().of(yup.string().required()).label("Subject Areas"),
  notes: yup.string().nullable().label("Notes"),
});

type ReviewerEditFields = yup.InferType<typeof schema>;

const emit = defineEmits<{
  success: [Reviewer];
  reset: [];
}>();

const { serverErrors: profileErrors, search } = useProfileAPI();
const {
  serverErrors,
  createReviewer: create,
  updateReviewer: update,
  isLoading,
} = useReviewEditorAPI();

const {
  errors,
  handleSubmit,
  handleReset,
  values,
  setValues,
  addUnsavedAlertListener,
  removeUnsavedAlertListener,
} = useForm<ReviewerEditFields>({
  schema,
  initialValues: {
    programmingLanguages: [],
    subjectAreas: [],
  },
  showPlaceholder: isLoading,
  onSubmit: async () => {
    await createOrUpdate();
  },
});

onMounted(() => {
  if (props.reviewer) setValues(JSON.parse(JSON.stringify(props.reviewer)));
  if (props.memberProfileId) values.memberProfileId = props.memberProfileId;
  addUnsavedAlertListener();
});

onBeforeUnmount(() => {
  removeUnsavedAlertListener();
});

function resetForm() {
  serverErrors.value = [];
  handleReset();
  if (props.reviewer) setValues(JSON.parse(JSON.stringify(props.reviewer)));
  if (props.memberProfileId) values.memberProfileId = props.memberProfileId;
}

function setMemberProfile(profile: RelatedMemberProfile) {
  values.memberProfileId = profile.id;
  values.memberProfile = profile;
}

async function createOrUpdate() {
  // FIXME: onsuccess should close the modal or emit something to tell the parent
  // to close it, probably doing the same thing elsewhere
  // const onSuccess = (response: any) => {
  //   window.location.href = detailUrl(response.data.id);
  // };
  if (!values.memberProfileId) return;
  let response;
  if (props.isEdit && props.reviewer) {
    response = await update(props.reviewer.id, values);
  } else {
    response = await create(values);
  }
  emit("success", response.data);
}

watch(
  () => props.reviewer,
  () => {
    if (props.reviewer) resetForm();
  }
);

defineExpose({ resetForm });
</script>
