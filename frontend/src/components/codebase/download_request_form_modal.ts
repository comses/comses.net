import { Component, Prop } from "vue-property-decorator";
import Vue from "vue";
import { api } from "@/api/connection";
import * as _ from "lodash";

@Component({
  template: `<div>
    <button
      class="btn btn-primary my-1 w-100"
      rel="nofollow"
      data-toggle="modal"
      data-target="#downloadSurvey"
    >
      <i class="fas fa-download"></i> Download Version {{ version_number }}
    </button>

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
                <div class="my-3">
                  <label for="inputEmail" class="form-label">Email</label>
                  <input
                    v-model="email"
                    type="email"
                    class="form-control"
                    id="inputEmail"
                    placeholder="name@example.com"
                  />
                </div>
                
                <div class="my-3">
                  <label for="inputIndustry" class="form-label">Industry</label>
                  <select 
                    v-model="selectedIndustry"
                    @change="updateIndustry()"
                    class="form-control"
                    id="inputIndustry"
                    placeholder=""
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
                        placeholder=""
                      />
                  </div>
                </div>

                <div class="my-3">
                  <label for="inputAffiliation" class="form-label">Affiliation</label>
                  <input
                    v-model="affiliation"
                    class="form-control"
                    id="inputAffiliation"
                    placeholder=""
                  />
                </div>

                <div class="my-3">
                  <label for="inputReason" class="form-label">Reason For Downloading</label>
                  <select 
                    v-model="selectedReason"
                    @change="updateReason()"
                    class="form-control"
                    id="inputReason"
                    placeholder=""
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
                        placeholder=""
                      />
                  </div>
                </div>

                <!--
                <div class="mb-3">
                  <label for="downloadReason" class="form-label"
                    >Reason for Download</label
                  >
                  <select
                    v-model="reason"
                    class="form-select"
                    id="downloadReason"
                    style="display: block;"
                  >
                    <option selected>Choose...</option>
                    <option value="1">One</option>
                    <option value="2">Two</option>
                    <option value="3">Three</option>
                    <option value="customOption">Other</option>
                  </select>
                </div>
                -->

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
              data-dismiss="modal"
              @click="submit"
              v-if="ajax_submit"
            >
              Submit
            </button>
            <form v-else>
              <button
                type="submit"
                class="btn btn-danger"
                data-dismiss="modal"
                formmethod="post"
                :formaction="url"
              >
                Submit
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>`,
})

export default class DownloadRequestFormModal extends Vue {
  @Prop({ default: true })
  public ajax_submit: boolean;

  @Prop()
  public url: string;

  @Prop()
  version_number: number;

  @Prop()
  public base_name: string;

  public errors: string[] = [];

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

  public email: string;
  public industry: string;
  public affiliation: string;
  public reason: string;

  get modalId() {
    return this.base_name;
  }

  get modalLabelId() {
    return `${this.base_name}Label`;
  }

  public async submit() {
    try {
      const response = await api.axios.post(this.url);
      this.errors = [];
      this.$emit("success", response.data);
      ($ as any)(`#${this.modalId}`).modal("hide");
    } catch (e) {
      if (_.isArray(_.get(e, "response.data"))) {
        this.errors = e.response.data;
      } else {
        this.$emit("error", e);
        this.errors = ["Submission failed"];
      }
    }
  }
}
