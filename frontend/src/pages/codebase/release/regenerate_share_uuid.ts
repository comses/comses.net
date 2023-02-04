import Vue from "vue";
import { Component, Prop } from "vue-property-decorator";
import { api } from "@/api/connection";

@Component({})
class RegenerateShareUUID extends Vue {
  @Prop()
  public absoluteUrl: string;

  @Prop()
  public initialShareUrl: string;

  public shareUrl: string = "";

  public handle;

  public created() {
    this.shareUrl = this.initialShareUrl;
  }

  public regenerateShareUuid() {
    api.axios.post(`${this.absoluteUrl}regenerate_share_uuid/`).then(r => (this.shareUrl = r.data));
  }
}

const el = document.getElementById("regenerate_share_uuid");
if (el) {
  const initialShareUrl = el.getAttribute("data-share-url");
  const absoluteUrl = el.getAttribute("data-absolute-url");
  new RegenerateShareUUID({ propsData: { initialShareUrl, absoluteUrl } }).$mount(el);
}
