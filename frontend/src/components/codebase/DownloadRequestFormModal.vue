<template>
  <div>
    <button
      class="btn btn-primary my-1 w-100"
      rel="nofollow"
      data-toggle="modal"
      data-target="#downloadRequestForm"
    >
      <i class="fas fa-download"></i> Download Version {{ versionNumber }}
    </button>
    <div
      class="modal fade"
      id="downloadRequestForm"
    >
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              Please complete a brief survey
              <button type="button" class="btn" data-bs-toggle="tooltip" data-bs-placement="top"
                title="This information helps us understand our community to better serve it.
                       Some answers are pre-filled from your profile.">
                <i class="text-info fas fa-question-circle"></i>
              </button>
            </h5>
              <button
                type="button"
                class="close"
                id="closeDownloadRequestFormModal"
                data-dismiss="modal"
              >&times;</button>
          </div>
          <div class="modal-body">
            <slot name="body"></slot>
            <div>
              <form class="align-items-center">
                <c-select
                  v-model="industry"
                  name="industry"
                  label="What industry do you work in?"
                  :options="industryOptions"
                  :errorMsgs="errors.industry"
                  :required="config.industry"
                ></c-select>
                <c-organization-search name="username" v-model="affiliation"
                  :errorMsgs="errors.affiliation"
                  :required="config.affiliation"
                  label="What is your institutional affiliation?" help="">
                </c-organization-search>
                <c-select
                  v-model="reason"
                  name="reason"
                  label="What do you plan on using this model for?"
                  :options="reasonOptions"
                  :errorMsgs="errors.reason"
                  :required="config.reason"
                ></c-select>
                <div class="form-check" v-if="authenticatedUser">
                  <input class="form-check-input" type="checkbox" v-model="save_to_profile" id="checkSaveToProfile">
                  <label class="form-check-label text-break" for="checkSaveToProfile">
                    <small>Save this information to my profile</small>
                  </label>
                </div>
              </form>
            </div>
          </div>
          <c-message-display
            :messages="statusMessages"
            @clear="statusMessages = []"
          ></c-message-display>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-success"
              @click="submit"
            >
              Submit and Download
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Prop } from "vue-property-decorator";
import Vue from "vue";
import { DismissOnSuccessHandler, HandlerWithRedirect } from "@/api/handler"
import { CodebaseReleaseAPI, ProfileAPI } from "@/api";
import { api } from '@/api/connection';
import { createFormValidator } from "@/pages/form";
import Input from "@/components/forms/input";
import Select from "@/components/forms/select";
import OrganizationSearch from "@/components/forms/organization";
import MessageDisplay from "@/components/messages";
import * as _ from "lodash";
import * as yup from "yup";

export const schema = yup.object().shape({
  industry: yup.string().required(),
  reason: yup.string().required(),
  affiliation: yup.object({
    name: yup.string().required(),
    url: yup.string().url().nullable(),
    acronym: yup.string().nullable(),
    ror_id: yup.string().nullable(),
  }).required(),
  save_to_profile: yup.boolean().required().default(false),
})

const codebaseReleaseAPI  = new CodebaseReleaseAPI();
const profileAPI = new ProfileAPI();

@Component({
  components: {
    "c-input": Input,
    "c-select": Select,
    "c-message-display": MessageDisplay,
    "c-organization-search": OrganizationSearch,
  },
})

export default class DownloadRequestFormModal extends createFormValidator(schema) {
  @Prop()
  public identifier: string;

  @Prop()
  public userId: number;

  @Prop()
  public userAffiliation: string;

  @Prop()
  public userIndustry: string;

  @Prop()
  public versionNumber: number;

  @Prop()
  public authenticatedUser: boolean;

  public industryOptions = [
    {value: 'university', label: 'College/University'},
    {value: 'educator', label: 'K-12 Educator'},
    {value: 'government', label: 'Government'},
    {value: 'private', label: 'Private'},
    {value: 'nonprofit', label: 'Non-Profit'},
    {value: 'student', label: 'Student'},
    {value: 'other', label: 'Other'},
  ];

  public reasonOptions = [
    {value: "research", label: 'Research'},
    {value: "education", label: 'Education'},
    {value: "commercial", label: 'Commercial'},
    {value: "policy", label: 'Policy / Planning'},
    {value: "other", label: 'Other'},
  ];                   

  public detailPageUrl(state) {
    return codebaseReleaseAPI.downloadUrl({identifier: this.identifier, version_number: this.versionNumber});
  }

  public created() {
    this.initializeForm();
  }

  public async initializeForm() {
    if (this.authenticatedUser) {
      this.state.affiliation = this.userAffiliation;
      this.state.industry = this.userIndustry ?? "";
    }
  }

  public async submit() {
    try {
      await this.validate();
      const response = await this.create();
      // temporary modal bug workaround
      document.getElementById("closeDownloadRequestFormModal").click();
      return response;
    } catch (e) {
      if (!(e instanceof yup.ValidationError)) {
        throw e;
      }
    }
  }

  public async create() {
    this.$emit("create");
    const handler = new HandlerWithRedirect(this);
    return codebaseReleaseAPI.requestDownload({identifier: this.identifier,version_number: this.versionNumber}, handler);
  }
}
</script>