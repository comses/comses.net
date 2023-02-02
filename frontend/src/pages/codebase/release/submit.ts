import { Component, Prop, Watch } from "vue-property-decorator";
import Vue from "vue";
import Checkbox from "@/components/forms/checkbox";
import Multiselect from "vue-multiselect";
import Input from "@/components/forms/input";

@Component({
  template: `<div>
    <button class="btn btn-primary" type="button" @click="submit">Submit</button>
    <div class="alert alert-danger" role="alert" v-if="validationMsg.type == 'error'">
      {{ validationMsg.msg }}
    </div>
    <div class="alert alert-success" role="alert" v-if="validationMsg.type == 'success'">
      {{ validationMsg.msg }}
    </div>
  </div>`,
  components: {
    "c-checkbox": Checkbox,
    "c-input": Input,
    Multiselect,
  },
})
export default class Submit extends Vue {
  public validationMsg: { type: "error" | "success" | "none"; msg: string } = {
    type: "none",
    msg: "",
  };

  @Watch("acceptTermsAndConditions")
  public onChangeAcceptTermsAndConditions() {
    this.validationMsg = { type: "none", msg: "" };
  }

  public submit() {
    this.$store
      .dispatch("submitIfValid")
      .then(response => (this.validationMsg = { type: "success", msg: "Submission Successful" }))
      .catch(response => (this.validationMsg = { type: "error", msg: "Submission Failed" }));
  }
}
