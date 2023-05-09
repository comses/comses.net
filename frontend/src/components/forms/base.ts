import Vue from "vue";
import { Component, Prop } from "vue-property-decorator";
import _ from "lodash-es";

@Component
export default class BaseControl extends Vue {
  @Prop({ default: true })
  public required;

  @Prop()
  public value;

  @Prop()
  public name: string;

  @Prop()
  public customId;

  @Prop({ default: () => [] })
  public errorMsgs: string[];

  get requiredClass() {
    return { required: this.required };
  }

  get controlId() {
    return _.isUndefined(this.customId) ? _.uniqueId(this.name) : this.customId;
  }

  get isInvalid() {
    return this.errorMsgs.length > 0;
  }

  get errorMessage() {
    return this.errorMsgs.join(", ");
  }

  public updateValue(value: any) {
    this.$emit("input", value);
  }
}
