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
            <h5 class="modal-title">Demographic Survey</h5>
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
                  label="Industry"
                  :options="industryOptions"
                  customOption="other"
                  :errorMsgs="errors.industry"
                  :required="config.industry"
                ></c-select>
                <c-input
                  v-model="affiliation.name"
                  name="affiliation"
                  label="Affiliation"
                  :errorMsgs="errors.affiliation"
                  :required="config.affiliation"
                ></c-input>
                <c-select
                  v-model="reason"
                  name="reason"
                  label="Reason For Downloading"
                  :options="reasonOptions"
                  customOption="other"
                  :errorMsgs="errors.reason"
                  :required="config.reason"
                ></c-select>
              </form>

              <!-- debug info -->
              <code>
              <p> industry: {{ industry }} </p>
              <p> affiliation: {{ affiliation.name }} </p>
              <p> reason: {{ reason }} </p>
              </code>
              <!-- -->

            </div>
          </div>
          <c-message-display
            :messages="statusMessages"
            @clear="statusMessages = []"
          ></c-message-display>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-dismiss="modal"
            >
              Close
            </button>
            <button
              type="button"
              class="btn btn-danger"
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
import { CodebaseReleaseAPI } from "@/api";
import { createFormValidator } from "@/pages/form";
import Input from "@/components/forms/input";
import Select from "@/components/forms/select";
import MessageDisplay from "@/components/messages";
import * as _ from "lodash";
import * as yup from "yup";

export const schema = yup.object().shape({
  industry: yup.string().required(),
  reason: yup.string().required(),
  affiliation: yup.object({
    name: yup.string().required(),
    url: yup.string().url().nullable(),
  }).required(),
})

const api  = new CodebaseReleaseAPI();

@Component({
  components: {
    "c-input": Input,
    "c-select": Select,
    "c-message-display": MessageDisplay,
    "c-institution-select": InstitutionSelect,
  },
})

export default class DownloadRequestFormModal extends createFormValidator(schema) {
  @Prop()
  public identifier: string;

  @Prop()
  public userAffiliation: string;

  @Prop()
  public userIndustry: string;

  @Prop()
  public versionNumber: number;

  @Prop()
  public authenticatedUser: boolean;

  // FIXME: get choices from server
  // OR remove entirely since choices with the option to have a custom entry doesn't make much sense
  public industryOptions = [
    "private",
    "university",
    "government",
    "nonprofit",
    "student",
    "educator",
    "other",
  ];

  public reasonOptions = [
    "research",
    "education",
    "commercial",
    "policy",
    "other",
  ];

  public detailPageUrl(state) {
    return api.downloadUrl({identifier: this.identifier, version_number: this.versionNumber});
  }

  public created() {
    this.initializeForm();
  }

  public async initializeForm() {
    if (this.authenticatedUser) {
      // FIXME: get whole affiliation object and update state
      this.state.affiliation.name = this.userAffiliation ?? "";
      this.state.industry = this.userIndustry ?? "";
    }
  }

  public async submit() {
    try {
      await this.validate();
      // temporary modal bug workaround
      document.getElementById("closeDownloadRequestFormModal").click();
      return this.create();
    } catch (e) {
      console.log(e);
      if (!(e instanceof yup.ValidationError)) {
        throw e;
      }
    }
  }

  public async create() {
    this.$emit("create");
    const handler = new HandlerWithRedirect(this);
    return api.requestDownload({identifier: this.identifier,version_number: this.versionNumber}, handler);
  }
}
</script>