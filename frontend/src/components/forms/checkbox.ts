import { Component, Prop } from "vue-property-decorator";
import BaseControl from "./base";

@Component({
  template: `<div class="form-check">
    <label :for="controlId" class="form-check-label">
      <input
        :id="controlId"
        type="checkbox"
        :name="name"
        :class="['form-check-input', {'is-invalid': isInvalid}]"
        :value="value"
        :checked="value === true"
        @change="toggle($event.target.value)"
      />
      <slot name="label" :label="label">
        <span :class="[requiredClass]">{{ label }}</span>
      </slot>
    </label>
    <slot name="help"
      ><small :aria-describedby="controlId" class="form-text text-muted">{{ help }}</small></slot
    >
    <div class="invalid-feedback">
      {{ errorMessage }}
    </div>
  </div>`,
})
class Checkbox extends BaseControl {
  @Prop({ default: "" })
  public validate: string;

  @Prop()
  public label: string;

  @Prop({ default: "" })
  public help: string;

  public toggle(value: string) {
    let v: boolean = false;
    if (value === "true") {
      v = true;
    }
    this.updateValue(!v);
  }
}

export default Checkbox;
