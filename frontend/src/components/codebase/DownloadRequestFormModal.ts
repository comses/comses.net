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

                <div class="mb-3">
                  <label for="downloadReason" class="form-label"
                    >Reason for Download</label
                  >
                  <select
                    v-model="reason"
                    class="form-select"
                    id="downloadReason"
                    style="display: inline;"
                  >
                    <option selected>Choose...</option>
                    <option value="1">One</option>
                    <option value="2">Two</option>
                    <option value="3">Three</option>
                    <option value="customOption">Other</option>
                  </select>
                </div>
              </form>
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
export class DownloadRequestFormModal extends Vue {
  @Prop({ default: true })
  public ajax_submit: boolean;

  @Prop()
  public url: string;

  @Prop()
  version_number: number;

  @Prop()
  public base_name: string;

  public errors: string[] = [];

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
