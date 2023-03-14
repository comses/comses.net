import { Component, Prop } from "vue-property-decorator";
import Vue from "vue";

@Component({
  template: `<div class="card border-light" v-if="messages && messages.length > 0">
    <div class="card-body px-0 py-0">
      <div v-for="m in messages" :class="m.classNames">
        {{ m.message }}
        <button type="button" class="close" data-bs-dismiss="alert" aria-label="Close" @click="clear">
          <span aria-hidden="true" class="pull-right"><span class="fas fa-times"></span></span>
        </button>
      </div>
    </div>
  </div>`,
})
export default class MessageDisplay extends Vue {
  @Prop()
  public messages?: Array<{ classNames: string; message: string }>;

  public clear() {
    this.$emit("clear");
  }
}
