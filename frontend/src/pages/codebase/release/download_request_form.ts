import Vue from "vue";
import { Component, Prop } from "vue-property-decorator";

import { api } from "@/api/connection";
import DownloadRequestFormModal from "@/components/codebase/DownloadRequestFormModal.vue";

@Component({
  components: {
    "c-download-request-form": DownloadRequestFormModal,
  },
})
class DownloadRequestForm extends Vue {
  @Prop()
  public absoluteUrl: string;

  @Prop()
  public initialShareUrl: string;

  public shareUrl: string = "";

  public handle;

  public created() {
    this.shareUrl = this.initialShareUrl;
  }
}

const el = document.getElementById("download-request-form");
if (el) {
  const userData = JSON.parse(el.getAttribute("data-user-data"));
  const versionNumber = el.getAttribute("data-version-number");
  new DownloadRequestFormModal({
    propsData: {
      versionNumber,
      userAffiliation: userData.affiliation, // FIXME: does this ever have data?
      userIndustry: userData.industry,
      userEmail: userData.email,
      authenticatedUser: !! userData.email, // for now, if no email in user data, assume not logged in
    },
  }).$mount(el);
}
