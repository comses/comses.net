<template>
  <div>
    <button
      class="btn btn-primary my-1 w-100"
      rel="nofollow"
      data-toggle="modal"
      data-target="#downloadRequestForm"
      @click="showEmail = !authenticatedUser"
    >
      <i class="fas fa-download"></i> Download Version {{ versionNumber }}
    </button>
    <div
      class="modal fade"
      id="downloadRequestForm"
    >
      <div class="modal-dialog">
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
                <div v-if="showEmail">
                  <c-input
                    v-model="email"
                    name="email"
                    label="Email"
                    :errorMsgs="errors.email"
                    :required="config.email"
                  ></c-input>
                </div>
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
                  v-model="affiliation"
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
              <p> email: {{ email }} </p>
              <p> industry: {{ industry }} </p>
              <p> affiliation: {{ affiliation }} </p>
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
  showEmail: yup.boolean(),
  email: yup.string().email().when("showEmail", {
    is: true,
    then: yup.string().required()
  }),
  industry: yup.string().required(),
  affiliation: yup.string().required(),
  reason: yup.string().required(),
})

const api  = new CodebaseReleaseAPI();

@Component({
  components: {
    "c-input": Input,
    "c-select": Select,
    "c-message-display": MessageDisplay,
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
  public userEmail: string;

  @Prop()
  public versionNumber: number;

  @Prop()
  public authenticatedUser: boolean;

  // FIXME: temp, get options from the server
  public industryOptions = [
    "private",
    "college/university",
    "government",
    "non-profit",
    "student",
    "K-12 educator",
    "other",
  ];

  public reasonOptions = [
    "research",
    "education",
    "commercial",
    "policy/planning",
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
      this.state.affiliation = this.userAffiliation ?? "";
      this.state.industry = this.userIndustry ?? "";
      this.state.email = this.userEmail ?? "";
    }
  }

  public async submit() {
    try {
      await this.validate();
      // FIXME: temporary modal bug workaround
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
    // TODO:  investigate why the server isn't creating new codebasereleasedownload rows.
    //        memberprofile is being updated, however.
    return api.requestDownload({identifier: this.identifier,version_number: this.versionNumber}, handler);
  }
}
</script>