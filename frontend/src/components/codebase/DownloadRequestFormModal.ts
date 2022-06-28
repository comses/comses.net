import { Component, Prop } from "vue-property-decorator";
import Vue from "vue";
import { api } from "@/api/connection";
import * as _ from "lodash";

@Component({
  template: `<a
      id="releaseDownload"
      class="btn btn-primary my-1 w-100"
      data-name="download"
      rel="nofollow"
      data-toggle="modal"
      data-target="#formModal"
    >
      <i class="fas fa-download"></i> Download Version {{ version_number }}
    </a>
  
  <div
      class="modal-fade"
      :id="modalId"
      role="dialog"
      :aria-labelledby="modalLabelId"
      aria-hidden="true"
    >
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" :id="modalLabelId">{{ title }}</h5>
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
              <form class="gy-2 gx-3 align-items-center">
                <div class="row mb-3">
                  <label for="inputEmail" class="col-sm-2 col-form-label"
                    >Email</label
                  >
                  <div class="col-sm-10">
                    <input type="email" class="form-control" id="inputEmail3" />
                  </div>
                </div>

                <div class="row mb-3">
                  <label for="downloadReason">Reason for Download</label>
                  <select class="form-select" id="downloadReason">
                    <option selected>Choose...</option>
                    <option value="1">One</option>
                    <option value="2">Two</option>
                    <option value="3">Three</option>
                  </select>
                </div>
              </form>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Clear/button>
            <button type="button" class="btn btn-danger" data-dismiss="modal" @click="submit" v-if="ajax_submit">Submit</button>
            <form v-else>
                <button type="submit" class="btn btn-danger" data-dismiss="modal" formmethod="post" :formaction="url">Submit</button>
            </form>
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
