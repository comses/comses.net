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
  const industry = el.getAttribute("data-industry");
  const affiliation = el.getAttribute("data-affiliation");
  const version_number = el.getAttribute("data-version-number");
  new DownloadRequestFormModal({
    propsData: { version_number, industry, affiliation },
  }).$mount(el);
}
