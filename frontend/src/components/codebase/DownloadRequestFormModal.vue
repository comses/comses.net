<template>
  <div>
    <button
      class="btn btn-primary my-1 w-100"
      rel="nofollow"
      data-toggle="modal"
      data-target="#downloadSurvey"
      @click="showEmail = anonymousUser"
    >
      <i class="fas fa-download"></i> Download Version {{ version_number }}
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
                <div v-if="anonymousUser">
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
              v-if="ajax_submit"
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
  @Prop({ default: true })
  public ajax_submit: boolean;

  @Prop()
  public url: string;

  @Prop()
  version_number: number;

  // FIXME: placeholder
  @Prop({ default: "downloadSurvey" })
  public base_name: string;

  // TODO: 
  @Prop({ default: true })
  public anonymousUser: boolean;

  public errors: string[] = [];

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

  public async initializeForm() {
    // TODO: retrieve + populate with user data
  }

  public async createOrUpdate() {
    // TODO: submit data
    // this.$emit('create-or-update');
    // let handler = new DismissOnSuccessHandler(this, this.modalId);
    // if (_.isNil(this.state.identifier)) {
    //   return api.create(handler);
    // } else {
    //   return api.update(this.state.identifier, handler);
    // }
  }

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