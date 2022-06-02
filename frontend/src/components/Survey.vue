<template>
  <div
    class="modal fade"
    id="surveyModal"
    tabindex="-1"
    role="dialog"
    aria-labelledby="surveyModalTitle"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-dialog-centered" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h4 class="modal-title" id="surveyModalTitle">Demographic Survey</h4>
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
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-dismiss="modal">
            Close
          </button>
          <button type="button" class="btn btn-primary">Submit</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from "vue-property-decorator";
import * as _ from "lodash";

@Component
export default class Survey extends Vue {
  // repopulate form with  fields
  created() {}
}
</script>
