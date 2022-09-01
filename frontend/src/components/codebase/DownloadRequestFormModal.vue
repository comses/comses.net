<template>
  <div>
    <button
      class="btn btn-primary my-1 w-100"
      rel="nofollow"
      data-toggle="modal"
      data-target="#downloadSurvey"
    >
      <i class="fas fa-download"></i> Download Version {{ version_number }}
    </button>
<!-- TODO: look into what ARIA stuff is doing -->
    <div
      class="modal fade"
      id="downloadSurvey"
      tab-index="-1"
      role="dialog"
      aria-labelledby="modalLabelId"
      aria-hidden="true"
    >
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" :id="modalLabelId">Demographic Survey</h5>
            <button
              type="button"
              class="close"
              data-dismiss="modal"
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
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
                <div class="my-3">
                  <label for="inputIndustry" class="form-label">Industry</label>
                  <!-- TODO: inline bootstrap validation errors for selections (class="invalid-feedback")-->
                  <select 
                    v-model="selectedIndustry"
                    @change="updateIndustry()"
                    class="form-control"
                    id="inputIndustry"
                    placeholder=""
                    :required="config.industry"
                    >
                    <option
                      :value="industryOption.value"
                      :selected="industryOption.value === selectedIndustry"
                      v-for="industryOption in industryOptions">
                      {{ industryOption.label }}
                    </option>
                  </select>
                  <div v-if="selectedIndustry === ''">
                    <label for="inputIndustryCustom" class="form-label"></label>
                      <input
                        v-model="industry"
                        class="form-control"
                        id="inputIndustryCustom"
                        placeholder="Other Industry"
                        :required="config.industry"
                      />
                  </div>
                </div>
                <c-input
                  v-model="affiliation"
                  name="affiliation"
                  label="Affiliation"
                  :errorMsgs="errors.affiliation"
                  :required="config.affiliation"
                ></c-input>
                <div class="my-3">
                  <label for="inputReason" class="form-label">Reason For Downloading</label>
                  <!-- TODO: inline bootstrap validation errors for selections (class="invalid-feedback")-->
                  <select 
                    v-model="selectedReason"
                    @change="updateReason()"
                    class="form-control"
                    id="inputReason"
                    placeholder=""
                    :required="config.reason"
                    >
                    <option
                      :value="reasonOption.value"
                      :selected="reasonOption.value === selectedReason"
                      v-for="reasonOption in reasonOptions">
                      {{ reasonOption.label }}
                    </option>
                  </select>
                  <div v-if="selectedReason === ''">
                    <label for="inputReasonCustom" class="form-label"></label>
                      <input
                        v-model="reason"
                        class="form-control"
                        id="inputReasonCustom"
                        placeholder="Reason for downloading"
                      />
                  </div>
                </div>
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
              Clear
            </button>
            <button
              type="button"
              class="btn btn-danger"
              @click="submit"
              v-if="ajax_submit"
            >
              Submit
            </button>
            <!-- <form v-else>
              <button
                type="submit"
                class="btn btn-danger"
                data-dismiss="modal"
                formmethod="post"
                :formaction="url"
              >
                Submit
              </button>
            </form> -->
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
import { createFormValidator } from "@/pages/form";
import Input from "@/components/forms/input";
import MessageDisplay from "@/components/messages";
import * as _ from "lodash";
import * as yup from "yup";

// FIXME: error message doesn't change on field update, validate on change, works in profile/Edit.vue
export const schema = yup.object().shape({
  email: yup.string().email().required(),
  industry: yup.string().required(),
  affiliation: yup.string().required(),
  reason: yup.string().required(),
})

@Component({
  components: {
    "c-input": Input,
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

  @Prop()
  public base_name: string;

  // TODO: redo props
  @Prop({ default: true })
  public anonymousUser: boolean;
  
  public errors: string[] = [];


  // TODO: presumably grab these options from the server
  public industryOptions: Array<{ value: string, label: string}>  = [
      { value: 'university', label: 'College/University' },
      { value: 'k12educator', label: 'K-12 Educator' },
      { value: 'government', label: 'Government'},
      { value: 'private', label: 'Private Use'},
      { value: 'nonprofit', label: 'Non-profit'},
      { value: '', label: 'Other (Enter Below)'},
  ];
  public selectedIndustry = 'none';

  public updateIndustry() {
    this.industry = this.selectedIndustry;
  }

  // TODO: presumably grab these options from the server
  public reasonOptions: Array<{ value: string, label: string}>  = [
      { value: 'research', label: 'Research' },
      { value: 'education', label: 'Education' },
      { value: 'commercial', label: 'Commercial'},
      { value: 'policy/planning', label: 'Policy/Planning'},
      { value: '', label: 'Other (Enter Below)'},
  ];
  public selectedReason = 'none';

  public updateReason() {
    this.reason = this.selectedReason;
  }

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
  }

  public async submit() {
    // DEBUG
    console.log(this.config.industry);
    try {
      const self: any = this;
      await self.validate();
      const response = await api.axios.post(this.url);
      this.errors = [];
      this.$emit("success", response.data);
      //($ as any)(`#${this.modalId}`).modal("hide");
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