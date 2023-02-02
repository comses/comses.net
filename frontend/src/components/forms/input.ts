import { Component, Prop } from "vue-property-decorator";
import BaseControl from "./base";

@Component({
  template: `<div class="form-group">
    <slot name="label">
      <label :for="controlId" :class="['form-control-label', requiredClass]">{{ label }}</label>
    </slot>
    <input
      :id="controlId"
      :type="type"
      :name="name"
      :class="['form-control', {'is-invalid': isInvalid}]"
      :value="value"
      @input="updateValue($event.target.value)"
    />
    <div class="invalid-feedback">
      {{ errorMessage }}
    </div>
    <slot name="help">
      <small :aria-describedby="controlId" class="form-text text-muted">{{ help }}</small>
    </slot>
  </div>`,
})
class Input extends BaseControl {
  @Prop({ default: "" })
  public validate: string;

  @Prop({ default: "text" })
  public type: string;

  @Prop({ default: "" })
  public label: string;

  @Prop({ default: "" })
  public help: string;

  public toggle(value: string) {
    let v: boolean = false;
    if (value === "true") {
      v = true;
    }
    this.$emit("input", !v);
  }
}

export default Input;
