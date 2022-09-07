<template>
  <div>
    <button
      class="btn btn-primary my-1 w-100"
      rel="nofollow"
      data-toggle="modal"
      data-target="#downloadSurvey"
      @click="showEmail = !authenticatedUser"
    >
      <i class="fas fa-download"></i> Download Version {{ versionNumber }}
    </button>
    <div
      class="modal fade"
      id="downloadSurvey"
    >
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" :id="modalLabelId">Demographic Survey</h5>
              <button
                type="button"
                class="close"
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
import { api } from "@/api/connection";
import DismissOnSuccessHandler from "@/api/handler"
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

@Component({
  components: {
    "c-input": Input,
    "c-select": Select,
    "c-message-display": MessageDisplay,
  },
})

export default class DownloadRequestFormModal extends createFormValidator(schema) {
  @Prop()
  public url: string;

  @Prop()
  public userAffiliation: string;

  @Prop()
  public userIndustry: string;

  @Prop()
  public userEmail: string;

  @Prop()
  public versionNumber: number;

  // FIXME: temp
  @Prop({ default: "downloadSurvey" })
  public base_name: string;

  @Prop()
  public authenticatedUser: boolean;

  public errors: string[] = [];

  // FIXME: temp
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

  get modalId() {
    return this.base_name;
  }

  get modalLabelId() {
    return `${this.base_name}Label`;
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

  // TODO: post data, close modal, and redirect to download
  public async submit() {
    try {
      const self: any = this;
      await self.validate();
      // const response = await api.axios.post(this.url);
      // this.errors = [];
      // this.$emit("success", response.data);
      // ($ as any)(`#${this.modalId}`).modal("hide");
    } catch (e) {
      if (!(e instanceof yup.ValidationError)) {
        if (_.isArray(_.get(e, "response.data"))) {
          this.errors = e.response.data;
        } else {
          this.$emit("error", e);
          this.errors = ["Submission failed"];
        }
        throw e;
      }
    }
  }
}
</script>