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
          <form>
            <div class="form-group">
              <label for="inputEmail">Email</label>
            </div>
            <div class="form-group">
              <label for="downloadReason">Reason for Download</label>
              <select class="form-control" id="downloadReason"></select>
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
